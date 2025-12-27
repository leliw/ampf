from typing import List, Optional

from pydantic import BaseModel, EmailStr


class AuthConfig(BaseModel):
    """Configuration for authentication."""

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_hours: int = 24 * 7  # Seven days
    reset_code_expire_minutes: int = 15
    jwt_secret_key: str


class DefaultUser(BaseModel):
    """Default user for the application"""

    username: str
    email: Optional[EmailStr] = None
    password: str
    roles: List[str] = ["admin"]


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
    subject: str = "Password reset"
    body_template: str = """Hello,
        
You are receiving this email because you requested a password reset.
To reset your password, please enter the following code into the form: {reset_code}
This code is valid for {reset_code_expire_minutes} minutes.
If you did not request a password reset, please ignore this email.
"""
