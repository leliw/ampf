from datetime import datetime
import hashlib
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, EmailStr, Field, model_serializer


class Tokens(BaseModel):
    """Tokens returned by the server when an user is successfully authenticated"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class TokenPayload(BaseModel):
    """Data stored in the token"""

    sub: str
    email: str | None = None
    name: str | None = None
    roles: Optional[List[str]] = Field(default_factory=lambda: [])
    picture: Optional[str] = None
    exp: datetime | None = None


class TokenExp(BaseModel):
    """Tuple of token and expiration time"""

    token: str
    exp: datetime


class AuthUser(BaseModel):
    """Base user model for authentication"""

    username: str
    email: str | None = None
    name: str | None = None
    disabled: bool = False
    roles: Optional[List[str]] = Field(default_factory=lambda: [])
    picture: Optional[str] = None
    password: Optional[str] | None = None
    hashed_password: Optional[str] | None = None
    reset_code: Optional[str] = None
    reset_code_exp: Optional[datetime] = None

    def __init__(self, **data):
        """If username is not provided, set it to email"""
        if not data.get("username") and data.get("email"):
            data["username"] = data.get("email")
        super().__init__(**data)

    @model_serializer
    def ser_model(self) -> Dict[str, Any]:
        """Remove sensitive fields before sending to client"""
        self.password = None
        self.hashed_password = None
        self.reset_code = None
        self.reset_code_exp = None
        return dict(self)


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
    roles: Optional[List[str]] = Field(default_factory=lambda: [])


class APIKeyInDB(APIKeyRequest):
    """API key stored in the database"""

    key_hash: str
    username: str


class APIKey(APIKeyInDB):
    """API key returned to the client"""

    key: str

    def __init__(self, **data):
        if not data.get("key"):
            data["key"] = str(uuid.uuid4())
        data["key_hash"] = hashlib.sha256(data["key"].encode()).hexdigest()
        super().__init__(**data)
