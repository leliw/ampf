from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from ampf.auth import DefaultUser, AuthConfig, ResetPasswordMailConfig, SmtpConfig
from ampf.base.base_factory import BaseFactory


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    version: str = "0.6.8"
    data_dir: str = "data"
    default_user: DefaultUser = DefaultUser()

    smtp: SmtpConfig = SmtpConfig()
    reset_password_mail: ResetPasswordMailConfig = ResetPasswordMailConfig()
    auth: AuthConfig = AuthConfig(jwt_secret_key="asdasdasd")
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
