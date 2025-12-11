import asyncio
import logging
from typing import Optional

import httpx

from .multi_service_token_manager import MultiServiceTokenManager

_log = logging.getLogger(__name__)


class BaseService:
    """
    Base class for interacting with external services.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
        token_manager: Optional[MultiServiceTokenManager] = None,
    ):
        """
        Initializes the BaseService with common configuration for API interactions.

        Args:
            base_url: The base URL of the external service.
            api_key: An optional API key for authentication. If not provided,
                     a token manager will be used.
            timeout: The default timeout for HTTP requests in seconds.
            token_manager: An optional MultiServiceTokenManager instance for
                           managing authentication tokens. If None, a new instance
                           will be created.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.token_manager = token_manager

    def _get_headers(self) -> dict:
        """
        Constructs the appropriate HTTP headers for requests,
        including authentication.

        Returns:
            A dictionary of HTTP headers.
        """
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return {}  # Application is running locally, no auth needed
        if self.api_key:
            return {"x-api-key": self.api_key}
        if self.token_manager:
            _log.debug("Getting token")
            token = self.token_manager.get_token_for(self.base_url)
            _log.debug("Token received %s...", token[:10])
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def _get_headers_async(self) -> dict:
        """
        Constructs the appropriate HTTP headers for requests,
        including authentication.

        Returns:
            A dictionary of HTTP headers.
        """
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return {}  # Application is running locally, no auth needed
        if self.api_key:
            return {"x-api-key": self.api_key}
        if self.token_manager:
            _log.debug("Getting token")
            token = await self.token_manager.get_token_for_async(self.base_url)
            _log.debug("Token received %s...", token[:10])
            return {"Authorization": f"Bearer {token}"}
        return {}


    async def ping(self) -> None:
        """
        Pings the service's health endpoint to check its availability.
        It retries multiple times with increasing delays if the service is
        unresponsive or returns a 5xx error.

        Raises:
            TimeoutError: If the service does not respond after multiple retries.
        """
        headers = await self._get_headers_async()
        timeout = httpx.Timeout(timeout=3.0, connect=1.0, read=2.0)
        _log.debug("Pinging service at %s", self.base_url)
        async with httpx.AsyncClient() as client:
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    _log.debug("Attempt %d to ping...", attempt + 1)
                    wait = 5 * (attempt + 1)
                    await client.get(url=f"{self.base_url}/api/ping", headers=headers, timeout=timeout)
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code >= 500:
                        _log.debug("Retry %d after %ds...", attempt + 1, wait)
                        await asyncio.sleep(wait)
                        continue
                except httpx.RequestError:
                    if attempt == max_retries - 1:
                        _log.debug("Final ping attempt failed.")
                        raise TimeoutError("Ping to knowledge base service timed out.")
                    _log.debug("Retry %d after %ds...", attempt + 1, wait)
                    await asyncio.sleep(wait)
