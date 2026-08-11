from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class Tokens(BaseModel):
    """Tokens returned by the server when an user is successfully authenticated"""

    access_token: str
    refresh_token: str | None = None
    token_type: str


class TokenPayload(BaseModel):
    """Data stored in the token"""

    sub: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = Field(default_factory=list)
    picture: str | None = None
    exp: datetime


class TokenExp(BaseModel):
    """Tuple of token and expiration time"""

    token: str
    exp: datetime


class BaseUser(BaseModel):
    username: str = ""
    email: EmailStr | None = None

    @field_validator("username", "email", mode="before")
    @classmethod
    def normalize_fields(cls, v):
        if isinstance(v, str):
            return v.lower().strip() or None
        return v

    @model_validator(mode="after")
    def ensure_email_and_username(self) -> "BaseUser":
        import re

        EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
        # Case 1: email provided → copy to username if missing
        if self.email and not self.username:
            self.username = self.email
        # Case 2: username provided (and it's a valid email) → copy to email if missing
        elif self.username and not self.email and EMAIL_REGEX.match(self.username):
            self.email = self.username
        # Case 3: neither provided → error
        elif not self.username and not self.email:
            raise ValueError("either 'email' or 'username' (in email format) must be provided")
        return self


class AuthUser(BaseUser):
    """Base user model for authentication"""

    name: str | None = None
    disabled: bool = False
    roles: list[str] = Field(default_factory=list)
    picture: str | None = None
    password: str | None = None
    hashed_password: str | None = None
    reset_code: str | None = None
    reset_code_exp: datetime | None = None


class ChangePasswordData(BaseModel):
    """Data for changing password"""

    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    """Data for requesting password reset"""

    email: EmailStr


class ResetPassword(BaseModel):
    """Data for resetting password"""

    email: EmailStr
    reset_code: str
    new_password: str


class APIKeyRequest(BaseModel):
    """Data for generating API key"""

    exp: datetime | None = None
    roles: list[str] = Field(default_factory=list)


class APIKeyInDB(APIKeyRequest):
    """API key stored in the database"""

    key_hash: str
    username: str


class APIKey(APIKeyInDB):
    """API key returned to the client"""

    key: str

    def __init__(self, **data):
        import hashlib
        import uuid

        if not data.get("key"):
            data["key"] = str(uuid.uuid4())
        data["key_hash"] = hashlib.sha256(data["key"].encode()).hexdigest()
        super().__init__(**data)
