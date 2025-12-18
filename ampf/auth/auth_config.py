import re
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class AuthConfig(BaseModel):
    """Configuration for authentication."""

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_hours: int = 24 * 7  # Seven days
    reset_code_expire_minutes: int = 15
    jwt_secret_key: str


class DefaultUser(BaseModel):
    """Default user for the application"""

    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str = "admin"
    roles: List[str] = ["admin"]

    @field_validator("username", "email", mode="before")
    @classmethod
    def normalize_fields(cls, v):
        if isinstance(v, str):
            return v.lower().strip() or None
        return v

    @model_validator(mode="after")
    def ensure_email_and_username(self) -> "DefaultUser":
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


class SmtpConfig(BaseModel):
    """SMTP configuration for sending emails."""

    host: str = "smtp.gmail.com"
    port: int = 465
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = True


class ResetPasswordMailConfig(BaseModel):
    """Configuration for reset password emails."""

    sender: str = "admin@example.com"
    subject: str = "Resetowanie hasła"
    body_template: str = """Witaj!
        
Otrzymałeś ten email, ponieważ poprosiłeś o zresetowanie hasła.
Aby zresetować swoje hasło, wpisz kod: {reset_code} w formularzu.
Kod jest ważny przez {reset_code_expire_minutes} minut.
Jeśli nie prosiłeś o zresetowanie hasła, zignoruj ten email.
"""
