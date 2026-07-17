import secrets

from pydantic import BaseModel, EmailStr, Field


class GoogleOAuthConfig(BaseModel):
    google_oauth_client_id: str
    google_oauth_client_secret: str


class ExchangeCodePayload(BaseModel):
    exchange_code: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    email: EmailStr
    name: str
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
