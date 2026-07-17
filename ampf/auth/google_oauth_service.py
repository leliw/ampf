import logging
from urllib.parse import urlparse, urlunparse

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse

from ampf.base import BaseAsyncStorage

from .auth_service import AuthService
from .google_oauth_model import ExchangeCodePayload, GoogleOAuthConfig

_log = logging.getLogger(__name__)


class GoogleOAuthService:
    def __init__(
        self, auth_service: AuthService, storage: BaseAsyncStorage[ExchangeCodePayload], config: GoogleOAuthConfig
    ):
        """Google authentication service

        Args:
            auth_service: Authentication service
            storage: Storage for exchange codes
            config: Google OAuth configuration
        """
        self.auth_service = auth_service
        self.storage = storage
        self.oauth = OAuth()
        self.oauth.register(
            name="google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_id=config.google_oauth_client_id,
            client_secret=config.google_oauth_client_secret,
            client_kwargs={"scope": "openid email profile"},
        )

    async def authorize_redirect(self, request: Request, base_url: str | None = None):
        """Redirects to Google OAuth login page.

        Args:
            request: The request object.
            base_url: The base URL of the application (frontend!).
        Returns:
            RedirectResponse: Redirects to Google OAuth login page.
        """
        callback_url = str(request.url_for("auth_callback"))
        if base_url:
            request.session["oauth_base_url"] = base_url
            parsed_base = urlparse(base_url)
            parsed_callback = urlparse(callback_url)
            new_path = parsed_base.path.rstrip("/") + parsed_callback.path
            redirect_uri = urlunparse(
                parsed_callback._replace(scheme=parsed_base.scheme, netloc=parsed_base.netloc, path=new_path)
            )
        else:
            redirect_uri = callback_url
        _log.debug(redirect_uri)
        return await self.oauth.google.authorize_redirect(request, redirect_uri)

    async def auth_callback(self, request: Request):
        """Callback for Google OAuth login.

        Args:
            request: The request object.
        Returns:
            RedirectResponse: Redirects to login page.
        """
        token = await self.oauth.google.authorize_access_token(request)
        user = token["userinfo"]
        payload = ExchangeCodePayload(
            email=user.get("email"),
            name=user.get("name"),
            given_name=user.get("given_name"),
            family_name=user.get("family_name"),
            picture=user.get("picture"),
        )
        _log.info("Google login: %s", payload.email)
        await self.storage.create(payload)
        base_url = request.session.pop("oauth_base_url", None)
        if base_url:
            redirect_url = f"{base_url.rstrip('/')}/login?exchange-code={payload.exchange_code}"
        else:
            redirect_url = f"/login?exchange-code={payload.exchange_code}"
        return RedirectResponse(url=redirect_url)

    async def authorize_with_code(self, code: str):
        """Authorizes user with exchange code.

        Args:
            code: The exchange code.
        Returns:
            Tokens: User tokens.
        """
        _log.debug("Authorize with code: %s", code)
        payload = await self.storage.get(code)
        await self.storage.delete(code)
        _log.debug("Payload: %s", payload)
        return await self.auth_service.authorize_by_email(payload.email)
