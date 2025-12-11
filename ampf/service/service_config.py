from typing import Optional

from pydantic import BaseModel


class ServiceConfig(BaseModel):
    url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 60
