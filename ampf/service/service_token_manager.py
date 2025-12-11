from abc import ABC, abstractmethod
import asyncio


class ServiceTokenManager(ABC):
    """Manages identity tokens for a single service."""

    def __init__(self, audience: str):
        self.audience = audience

    @abstractmethod
    def get_token(self) -> str:
        pass

    async def get_token_async(self) -> str:
        # Simulate async operation
        await asyncio.sleep(0.01)
        return self.get_token()
