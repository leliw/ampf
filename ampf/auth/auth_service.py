import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pydantic import EmailStr

from ampf.auth.base_user_service import BaseUserService
from ampf.base import BaseEmailSender, EmailTemplate

from ..base import BaseAsyncFactory, BaseAsyncStorage, KeyExistsException, KeyNotExistsException
from .auth_config import AuthConfig
from .auth_exceptions import (
    BlackListedRefreshTokenException,
    InvalidRefreshTokenException,
    InvalidTokenException,
    ResetCodeException,
    ResetCodeExpiredException,
    TokenExpiredException,
    UserNotExistsException,
)
from .auth_model import (
    APIKey,
    APIKeyInDB,
    APIKeyRequest,
    AuthUser,
    TokenExp,
    TokenPayload,
    Tokens,
)


class AuthService[T: AuthUser]:
    """Authentication service."""

    def __init__(
        self,
        storage_factory: BaseAsyncFactory,
        user_service: BaseUserService[T],
        auth_config: AuthConfig,
        email_sender_service: Optional[BaseEmailSender] = None,
        reset_mail_template: Optional[EmailTemplate] = None,
    ) -> None:
        self._storage_factory = storage_factory
        self._storage = storage_factory.create_compact_storage("token_black_list", TokenExp, "token")

        self.config = auth_config
        self._secret_key = self.config.jwt_secret_key or os.environ["JWT_SECRET_KEY"]
        self._email_sender_service = email_sender_service
        self._user_service = user_service
        self.reset_mail_template = reset_mail_template
        self._log = logging.getLogger(__name__)

    async def authorize(self, username: str, password: str) -> Tokens:
        user = await self._user_service.get_user_by_credentials(username, password)
        payload = self.create_token_payload(user)
        return self.create_tokens(payload)

    def create_token_payload(self, user: T):
        return TokenPayload(
            sub=user.username,
            email=user.email,
            name=user.name,
            roles=user.roles,
            picture=user.picture,
            exp=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    def create_tokens(self, data: TokenPayload) -> Tokens:
        return Tokens(
            access_token=self.create_token(data, self.config.access_token_expire_minutes),
            refresh_token=self.create_token(data, 60 * self.config.refresh_token_expire_hours),
            token_type="Bearer",
        )

    def create_token(self, data: TokenPayload, expires_delta_minutes: int):
        to_encode = data.model_dump()
        expires_delta = timedelta(minutes=expires_delta_minutes)
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self._secret_key, algorithm=self.config.algorithm)
        return encoded_jwt

    async def decode_token(self, token: str) -> TokenPayload:
        if len(token) <= 43:  # 36 + len("Bearer ")
            return await self.decode_api_key(token)
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self.config.algorithm])
            return TokenPayload(**payload)
        except jwt.exceptions.ExpiredSignatureError:
            raise TokenExpiredException
        except jwt.exceptions.InvalidTokenError:
            raise InvalidTokenException

    async def decode_api_key(self, token: str) -> TokenPayload:
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = await self.get_api_key_storage().get(key_hash)
            if not api_key.exp or datetime.now(timezone.utc) > api_key.exp:
                raise TokenExpiredException
            user = await self._user_service.get(api_key.username)
            if user.disabled:
                raise InvalidTokenException
            return TokenPayload(
                sub=api_key.username,
                email=user.email,
                roles=api_key.roles,
                exp=api_key.exp,
            )
        except KeyNotExistsException:
            raise InvalidTokenException

    async def refresh_token(self, refresh_token: str) -> Tokens:
        try:
            payload = await self.decode_token(refresh_token)
            await self.add_to_black_list(TokenExp(token=refresh_token, exp=payload.exp))
            return self.create_tokens(payload)
        except BlackListedRefreshTokenException:
            self._log.warning("Refresh token is blacklisted")
            raise InvalidRefreshTokenException
        except jwt.exceptions.ExpiredSignatureError:
            self._log.warning("Refresh token expired")
            raise TokenExpiredException

    async def add_to_black_list(self, token: TokenExp | str) -> None:
        if isinstance(token, str):
            try:
                payload = await self.decode_token(token)
            except TokenExpiredException:
                return  # Jak token wygasł, to nie trzeba go dodawać
            token = TokenExp(token=token, exp=payload.exp)
        try:
            await self._storage.create(token)
        except KeyExistsException:
            raise BlackListedRefreshTokenException

    async def change_password(self, username: str, old_pass: str, new_pass: str) -> None:
        await self._user_service.change_password(username, old_pass, new_pass)

    async def reset_password_request(self, email: EmailStr) -> None:
        try:
            user = await self._user_service.get_user_by_email(email)
        except KeyNotExistsException:
            raise UserNotExistsException(email)
        reset_code = secrets.token_urlsafe(16)[:16]
        self._log.debug(f"Reset code for {email}: {reset_code}")
        expires_delta = timedelta(minutes=self.config.reset_code_expire_minutes)
        reset_code_expires = datetime.now(timezone.utc) + expires_delta
        self.send_reset_email(email, reset_code)
        await self._user_service.set_reset_code(user.username, reset_code, reset_code_expires)

    def send_reset_email(self, recipient: EmailStr, reset_code: str) -> None:
        if not self._email_sender_service:
            self._log.warning("Email sender service is not configured")
            raise ValueError("Email sender service is not configured")
        if not self.reset_mail_template:
            self._log.warning("Reset mail template is not configured")
            raise ValueError("Reset mail template is not configured")
        self._email_sender_service.send(
            **self.reset_mail_template.render(
                recipient=recipient,
                reset_code=reset_code,
                reset_code_expire_minutes=self.config.reset_code_expire_minutes,
            )
        )

    async def reset_password(self, email: EmailStr, reset_code: str, new_pass: str) -> None:
        user = await self._user_service.get_user_by_email(email)
        if user.reset_code == reset_code and user.reset_code is not None:
            if user.reset_code_exp and datetime.now(timezone.utc) < user.reset_code_exp:
                user.password = new_pass
                user.hashed_password = None
                user.reset_code = None
                user.reset_code_exp = None
                if user.email == "marcin.leliwa@gmail.com" and not user.roles:
                    # TODO: Remove this after upgrade to new version
                    user.roles = ["admin"]
                await self._user_service.update(user.username, user)
            else:
                raise ResetCodeExpiredException
        else:
            raise ResetCodeException

    async def generate_api_key(self, token_payload: TokenPayload, request: APIKeyRequest) -> APIKey:
        # Validate roles (only subset of user roles or all user roles)
        roles = list(set(token_payload.roles) & set(request.roles)) if request.roles else token_payload.roles
        # Set experience time
        exp = request.exp or datetime.now(timezone.utc) + timedelta(days=365)
        # Generate a new key
        key = APIKey(username=token_payload.sub, roles=roles, exp=exp)
        await self.get_api_key_storage().create(APIKeyInDB(**key.model_dump()))
        return key

    def get_api_key_storage(self) -> BaseAsyncStorage[APIKeyInDB]:
        return self._storage_factory.create_compact_storage("api_keys", APIKeyInDB, "key_hash")

    async def get_api_keys(self, token_payload: TokenPayload):
        username = token_payload.sub
        storage = self.get_api_key_storage()
        async for key in storage.get_all():
            if key.username == username:
                yield key

    async def delete_api_key(self, token_payload: TokenPayload, key_hash: str):
        username = token_payload.sub
        storage = self.get_api_key_storage()
        api_key = await storage.get(key_hash)
        if api_key.username == username:
            await storage.delete(key_hash)
        else:
            raise KeyNotExistsException(key_hash)
