from pydantic import BaseModel


class ServiceConfig(BaseModel):
    url: str | None = None
    api_key: str | None = None
    timeout: int = 60

    @property
    def required_url(self) -> str:
        if not self.url:
            raise ValueError("Service URL is required")
        return self.url

    @property
    def required_api_key(self) -> str:
        if not self.api_key:
            raise ValueError("Service API key is required")
        return self.api_key
