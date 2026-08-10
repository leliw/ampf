from .auth_config import AuthConfig, DefaultUser, ResetPasswordMailConfig, SmtpConfig
from .auth_exceptions import (
    BlackListedRefreshTokenException,
    InsufficientPermissionsError,
    InvalidRefreshTokenException,
    InvalidTokenException,
    TokenExpiredException,
)
from .auth_model import (
    APIKey,
    APIKeyInDB,
    APIKeyRequest,
    AuthUser,
    ChangePasswordData,
    ResetPassword,
    ResetPasswordRequest,
    TokenExp,
    TokenPayload,
    Tokens,
)
from .auth_service import AuthService
from .base_user_service import BaseUserService

__all__ = [
    "APIKey",
    "APIKeyInDB",
    "APIKeyRequest",
    "AuthConfig",
    "AuthService",
    "AuthUser",
    "BaseUserService",
    "BlackListedRefreshTokenException",
    "ChangePasswordData",
    "DefaultUser",
    "InsufficientPermissionsError",
    "InvalidRefreshTokenException",
    "InvalidTokenException",
    "ResetPassword",
    "ResetPasswordMailConfig",
    "ResetPasswordRequest",
    "SmtpConfig",
    "TokenExp",
    "TokenExpiredException",
    "TokenPayload",
    "Tokens",
]


try:
    from .google_oauth_model import ExchangeCodePayload, GoogleOAuthConfig  # noqa: F401
    from .google_oauth_service import GoogleOAuthService  # noqa: F401
    __all__.append("GoogleOAuthService")
    __all__.append("GoogleOAuthConfig")
    __all__.append("ExchangeCodePayload")
except ImportError:
    pass

try:
    from .google_oauth import GoogleOAuth  # noqa: F401

    __all__.append("GoogleOAuth")

except ImportError:
    pass
