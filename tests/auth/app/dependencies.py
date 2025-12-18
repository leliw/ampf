from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ampf.auth import AuthService, TokenPayload
from ampf.auth.auth_exceptions import InsufficientPermissionsError
from ampf.auth.auth_service import AuthConfig
from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.base_email_sender import BaseEmailSender
from ampf.base.email_template import EmailTemplate
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory

from .config import ServerConfig
from .features.user.user_service import UserService

AuthTokenDep = Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="api/login"))]


def get_server_config() -> ServerConfig:
    return ServerConfig(auth=AuthConfig(jwt_secret_key="asdasdasd"))


ServerConfigDep = Annotated[ServerConfig, Depends(get_server_config)]


async def get_async_factory() -> BaseAsyncFactory:
    return InMemoryAsyncFactory()


AsyncFactoryDep = Annotated[BaseAsyncFactory, Depends(get_async_factory)]


def user_service_dep(factory: AsyncFactoryDep) -> UserService:
    return UserService(factory)


UserServceDep = Annotated[UserService, Depends(user_service_dep)]


async def get_email_sender(conf: ServerConfigDep) -> Optional[BaseEmailSender]:
    return None


EmailSenderServiceDep = Annotated[BaseEmailSender, Depends(get_email_sender)]


async def auth_service_dep(
    factory: AsyncFactoryDep,
    email_sender_service: EmailSenderServiceDep,
    server_config: ServerConfigDep,
    user_service: UserServceDep,
) -> AuthService:
    reset_mail_template = EmailTemplate(**dict(server_config.reset_password_mail))
    return AuthService(
        storage_factory=factory,
        email_sender_service=email_sender_service,
        user_service=user_service,
        reset_mail_template=reset_mail_template,
        auth_config=server_config.auth,
    )


AuthServiceDep = Annotated[AuthService, Depends(auth_service_dep)]


async def decode_token(auth_service: AuthServiceDep, token: AuthTokenDep) -> TokenPayload:
    return await auth_service.decode_token(token)


TokenPayloadDep = Annotated[TokenPayload, Depends(decode_token)]


class Authorize:
    """Dependency for authorizing users based on their role."""

    def __init__(self, required_role: Optional[str] = None):
        self.required_role = required_role

    def __call__(self, token_payload: TokenPayloadDep) -> bool:
        if not self.required_role or self.required_role in token_payload.roles:
            return True
        else:
            raise InsufficientPermissionsError()
