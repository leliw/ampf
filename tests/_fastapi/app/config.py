from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    version: str = "0.1.0"
    data_dir: str = "./data/"
    gcp_root_storage: Optional[str] = None
    gcp_bucket_name: Optional[str] = None


class ClientConfig(BaseModel):
    version: str
