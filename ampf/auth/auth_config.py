from typing import List, Optional

from pydantic import BaseModel

from .auth_model import BaseUser


class AuthConfig(BaseModel):
    """Configuration for authentication."""

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_hours: int = 24 * 7  # Seven days
    reset_code_expire_minutes: int = 15
    jwt_secret_key: str


class DefaultUser(BaseUser):
    """Default user for the application"""

    password: str = "admin"
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
    subject: str = "Resetowanie hasła"
    body_template: str = """Witaj!
        
Otrzymałeś ten email, ponieważ poprosiłeś o zresetowanie hasła.
Aby zresetować swoje hasło, wpisz kod: {reset_code} w formularzu.
Kod jest ważny przez {reset_code_expire_minutes} minut.
Jeśli nie prosiłeś o zresetowanie hasła, zignoruj ten email.
"""
