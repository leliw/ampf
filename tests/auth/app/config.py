from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from ampf.auth import DefaultUser
from ampf.base.base_factory import BaseFactory


class AuthConfig(BaseModel):
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_hours: int = 24 * 7  # Seven days
    reset_code_expire_minutes: int = 15


class SmtpConfig(BaseModel):
    host: str = "smtp.gmail.com"
    port: int = 465
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = True


class ResetPasswordMailConfig(BaseModel):
    sender: str = "admin@example.com"
    subject: str = "Resetowanie hasła - Chat"
    body_template: str = """Witaj!
        
Otrzymałeś ten email, ponieważ poprosiłeś o zresetowanie hasła.
Aby zresetować swoje hasło, wpisz kod: {reset_code} w formularzu.
Kod jest ważny przez {reset_code_expire_minutes} minut.
Jeśli nie prosiłeś o zresetowanie hasła, zignoruj ten email.
"""


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    version: str = "0.6.8"
    data_dir: str = "data"
    jwt_secret_key: str
    default_user: DefaultUser = DefaultUser()

    smtp: SmtpConfig = SmtpConfig()
    reset_password_mail: ResetPasswordMailConfig = ResetPasswordMailConfig()
    auth: AuthConfig = AuthConfig()
    profiler: bool = False


class ClientConfig(BaseModel):
    version: str
    google_oauth_client_id: str


# UserConfig isn't used jet !!!!
# The key should be username
class UserConfig(BaseModel):
    agent: Optional[str] = None


class UserConfigService:
    def __init__(self, factory: BaseFactory):
        self.storage = factory.create_compact_storage(
            "user_config", UserConfig, key_name="config"
        )

    def get(self) -> UserConfig:
        return self.storage.get("config")

    def put(self, config: UserConfig):
        self.storage.put("config", config)

    def patch(self, patch_data: UserConfig) -> None:
        key = "config"
        item = self.storage.get(key)
        patch_dict = patch_data.model_dump(exclude_unset=True)
        item.__dict__.update(patch_dict)
        self.storage.put(key, item)
