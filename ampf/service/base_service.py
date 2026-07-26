import asyncio
import logging

import httpx2
from pydantic import BaseModel

from .multi_service_token_manager import MultiServiceTokenManager

_log = logging.getLogger(__name__)


class BaseService:
    """
    Base class for interacting with external services.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 60,
        token_manager: MultiServiceTokenManager | None = None,
        httpx_async_client: httpx2.AsyncClient | None = None,
        httpx_client: httpx2.Client | None = None,
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
            httpx_async_client: An optional httpx2.AsyncClient instance for making
                                asynchronous HTTP requests. If None, a new instance
                                will be created.
            httpx_client: An optional httpx2.Client instance for making HTTP requests. 
                                If None, a new instance will be created.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.token_manager = token_manager
        self.httpx_async_client = httpx_async_client
        self.httpx_client = httpx_client

    def _get_client(self) -> httpx2.Client:
        if not self.httpx_client:
            self.httpx_client = httpx2.Client()
        return self.httpx_client

    def _get_async_client(self) -> httpx2.AsyncClient:
        if not self.httpx_async_client:
            self.httpx_async_client = httpx2.AsyncClient()
        return self.httpx_async_client

    async def post(self, endpoint: str, json: dict | BaseModel) -> httpx2.Response:
        response = await self._get_async_client().post(
            url=f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            headers=await self._get_headers_async(),
            json=json if isinstance(json, dict) else json.model_dump(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def post_typed[T: BaseModel](self, endpoint: str, ret_clazz: type[T], json: dict | BaseModel) -> T:
        response = self._get_client().post(
            url=f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            headers=self._get_headers(),
            json=json if isinstance(json, dict) else json.model_dump(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        resp = response.json()
        return ret_clazz.model_validate(resp)

    async def post_typed_async[T: BaseModel](self, endpoint: str, ret_clazz: type[T], json: dict | BaseModel) -> T:
        response = await self._get_async_client().post(
            url=f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            headers=await self._get_headers_async(),
            json=json if isinstance(json, dict) else json.model_dump(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        resp = response.json()
        return ret_clazz.model_validate(resp)

    async def get(
        self, endpoint: str, params: dict | None = None, timeout: httpx2.Timeout | int | None = None
    ) -> httpx2.Response:
        response = await self._get_async_client().get(
            url=f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            headers=await self._get_headers_async(),
            params=params,
            timeout=timeout if timeout is not None else self.timeout,
        )
        response.raise_for_status()
        return response

    def get_typed[T: BaseModel](
        self, endpoint: str, ret_clazz: type[T], params: dict | None = None, timeout: httpx2.Timeout | int | None = None
    ) -> T:
        response = self._get_client().get(
            url=f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            headers=self._get_headers(),
            params=params,
            timeout=timeout if timeout is not None else self.timeout,
        )
        response.raise_for_status()
        resp = response.json()
        return ret_clazz.model_validate(resp)

    async def get_typed_async[T: BaseModel](
        self, endpoint: str, ret_clazz: type[T], params: dict | None = None, timeout: httpx2.Timeout | int | None = None
    ) -> T:
        response = await self._get_async_client().get(
            url=f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            headers=await self._get_headers_async(),
            params=params,
            timeout=timeout if timeout is not None else self.timeout,
        )
        response.raise_for_status()
        resp = response.json()
        return ret_clazz.model_validate(resp)

    async def _get_headers_async(self) -> dict:
        """
        Constructs the appropriate HTTP headers for requests,
        including authentication.

        Returns:
            A dictionary of HTTP headers.
        """
        if self.base_url.startswith("http://"):
            return {}  # Application is running locally, no auth needed
        if self.api_key:
            return {"x-api-key": self.api_key}
        if self.token_manager:
            _log.debug("Getting token")
            token = await self.token_manager.get_token_for_async(self.base_url)
            _log.debug("Token received %s...", token[:10] if token else "None")
            if token:
                return {"Authorization": f"Bearer {token}"}
        return {}

    def _get_headers(self) -> dict:
        """
        Constructs the appropriate HTTP headers for requests,
        including authentication.

        Returns:
            A dictionary of HTTP headers.
        """
        if self.base_url.startswith("http://"):
            return {}  # Application is running locally, no auth needed
        if self.api_key:
            return {"x-api-key": self.api_key}
        if self.token_manager:
            _log.debug("Getting token")
            token = self.token_manager.get_token_for(self.base_url)
            _log.debug("Token received %s...", token[:10] if token else "None")
            if token:
                return {"Authorization": f"Bearer {token}"}
        return {}

    async def ping(self, endpoint: str = "/api/ping") -> None:
        """
        Pings the service's health endpoint to check its availability.
        It retries multiple times with increasing delays if the service is
        unresponsive or returns a 5xx error.

        Raises:
            TimeoutError: If the service does not respond after multiple retries.
        """
        timeout = httpx2.Timeout(timeout=3.0, connect=1.0, read=2.0)
        _log.debug("Pinging service at %s", self.base_url)
        max_retries = 5
        for attempt in range(max_retries):
            wait = 5 * (attempt + 1)
            try:
                _log.debug("Attempt %d to ping...", attempt + 1)
                await self.get(endpoint, timeout=timeout)
                _log.debug("Ping to %s successful.", self.base_url)
                break
            except httpx2.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    _log.debug("Retry %d after %ds...", attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue
                if e.response.status_code >= 400:
                    raise
            except httpx2.RequestError:
                if attempt == max_retries - 1:
                    _log.debug("Final ping attempt failed.")
                    raise TimeoutError(f"Service at {self.base_url} timed out.")
                _log.debug("Retry %d after %ds...", attempt + 1, wait)
                await asyncio.sleep(wait)
