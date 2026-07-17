
from pydantic_settings import BaseSettings, SettingsConfigDict

from ampf.auth import AuthConfig, DefaultUser, ResetPasswordMailConfig, SmtpConfig


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    version: str = "0.6.8"
    data_dir: str = "data"

    default_user: DefaultUser = DefaultUser(username="admin", password="admin")

    smtp: SmtpConfig = SmtpConfig()
    reset_password_mail: ResetPasswordMailConfig = ResetPasswordMailConfig()
    auth: AuthConfig = AuthConfig(jwt_secret_key="asdasdasd")
