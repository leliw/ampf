import asyncio
import logging
from typing import TypeVar

import httpx2
from httpx2._types import RequestContent, RequestData, RequestFiles
from pydantic import BaseModel

from .multi_service_token_manager import MultiServiceTokenManager

_log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


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

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    @staticmethod
    def _serialize_json(value: dict | BaseModel | None) -> dict | None:
        if value is None or isinstance(value, dict):
            return value
        return value.model_dump(mode="json")

    def _get_client(self) -> httpx2.Client:
        if self.httpx_client is None:
            self.httpx_client = httpx2.Client()
        return self.httpx_client

    def _get_async_client(self) -> httpx2.AsyncClient:
        if self.httpx_async_client is None:
            self.httpx_async_client = httpx2.AsyncClient()
        return self.httpx_async_client

    def _validate_response(self, response: httpx2.Response, model: type[T]) -> T:
        response.raise_for_status()
        return model.model_validate(response.json())

    # ------------------------------------------------------------------
    # Raw requests
    # ------------------------------------------------------------------

    def _request_sync(
        self,
        method: str,
        endpoint: str,
        *,
        timeout: httpx2.Timeout | int | None = None,
        **kwargs,
    ) -> httpx2.Response:
        try:
            response = self._get_client().request(
                method=method,
                url=self._url(endpoint),
                headers=self._get_headers_sync(),
                timeout=self.timeout if timeout is None else timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response

        except httpx2.ConnectError as e:
            _log.error(
                "Service %s is unreachable: %s",
                self.base_url,
                e,
            )
            raise

        except httpx2.HTTPStatusError as e:
            _log.error(
                "HTTP error %s for %s %s: %s",
                e.response.status_code,
                method,
                self._url(endpoint),
                e,
            )
            raise

    async def _request_async(
        self,
        method: str,
        endpoint: str,
        *,
        timeout: httpx2.Timeout | int | None = None,
        **kwargs,
    ) -> httpx2.Response:
        try:
            response = await self._get_async_client().request(
                method=method,
                url=self._url(endpoint),
                headers=await self._get_headers_async(),
                timeout=self.timeout if timeout is None else timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response

        except httpx2.ConnectError as e:
            _log.error(
                "Service %s is unreachable: %s",
                self.base_url,
                e,
            )
            raise

        except httpx2.HTTPStatusError as e:
            _log.error(
                "HTTP error %s for %s %s: %s",
                e.response.status_code,
                method,
                self._url(endpoint),
                e,
            )
            raise

    def post_sync(
        self,
        endpoint: str,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: dict | BaseModel | None = None,
        params: dict | None = None,
    ) -> httpx2.Response:
        return self._request_sync(
            "POST",
            endpoint,
            content=content,
            data=data,
            files=files,
            json=self._serialize_json(json),
            params=params,
        )

    async def post(
        self,
        endpoint: str,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: dict | BaseModel | None = None,
        params: dict | None = None,
    ) -> httpx2.Response:
        return await self._request_async(
            "POST",
            endpoint,
            content=content,
            data=data,
            files=files,
            json=self._serialize_json(json),
            params=params,
        )

    def get_sync(
        self,
        endpoint: str,
        params: dict | None = None,
        timeout: httpx2.Timeout | int | None = None,
    ) -> httpx2.Response:
        return self._request_sync("GET", endpoint, params=params, timeout=timeout)

    async def get(
        self,
        endpoint: str,
        params: dict | None = None,
        timeout: httpx2.Timeout | int | None = None,
    ) -> httpx2.Response:
        return await self._request_async("GET", endpoint, params=params, timeout=timeout)

    # ------------------------------------------------------------------
    # Typed API
    # ------------------------------------------------------------------

    def post_typed_sync(
        self,
        endpoint: str,
        ret_clazz: type[T],
        json: dict | BaseModel,
    ) -> T:
        response = self.post_sync(endpoint, json=json)
        return self._validate_response(response, ret_clazz)

    async def post_typed(
        self,
        endpoint: str,
        ret_clazz: type[T],
        json: dict | BaseModel,
    ) -> T:
        response = await self.post(endpoint, json=json)
        return self._validate_response(response, ret_clazz)

    def get_typed_sync(
        self,
        endpoint: str,
        ret_clazz: type[T],
        params: dict | None = None,
        timeout: httpx2.Timeout | int | None = None,
    ) -> T:
        response = self.get_sync(
            endpoint,
            params=params,
            timeout=timeout,
        )
        return self._validate_response(response, ret_clazz)

    async def get_typed(
        self,
        endpoint: str,
        ret_clazz: type[T],
        params: dict | None = None,
        timeout: httpx2.Timeout | int | None = None,
    ) -> T:
        response = await self.get(
            endpoint,
            params=params,
            timeout=timeout,
        )
        return self._validate_response(response, ret_clazz)

    def _get_headers_from_token(self, token: str | None) -> dict[str, str]:
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _get_headers_sync(self) -> dict[str, str]:
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
            return self._get_headers_from_token(token)

        return {}

    async def _get_headers_async(self) -> dict[str, str]:
        if self.base_url.startswith("http://"):
            return {}

        if self.api_key:
            return {"x-api-key": self.api_key}

        if self.token_manager:
            token = await self.token_manager.get_token_for_async(self.base_url)
            return self._get_headers_from_token(token)

        return {}

    async def ping(self, endpoint: str = "/api/ping") -> None:
        """
        Wakes up the Cloud Run service and verifies that it is ready.

        The request is retried when the service returns a 5xx response or when
        a transport-level error occurs. Client errors (4xx) are not retried.

        Raises:
            TimeoutError: If the service does not become ready after all retries.
            httpx2.HTTPStatusError: If the health endpoint returns a 4xx response.
        """
        timeout = httpx2.Timeout(timeout=3.0, connect=1.0, read=2.0)
        _log.debug("Pinging service at %s", self.base_url)
        max_retries = 5
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                _log.debug("Ping attempt %d/%d to %s", attempt + 1, max_retries, self.base_url)
                await self.get(endpoint, timeout=timeout)
                _log.debug("Service %s is awake and ready", self.base_url)
                return
            except httpx2.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code < 500:
                    _log.error("Endpoint %s returned non-retryable HTTP status %s", self.base_url, status_code)
                    raise
                last_error = exc
                _log.debug("Service %s returned HTTP %s; retrying", self.base_url, status_code)
            except httpx2.RequestError as exc:
                last_error = exc
                _log.debug("Request to service %s failed; retrying: %s", self.base_url, exc)

            if attempt == max_retries - 1:
                break
            delay = min(2**attempt, 10)
            _log.debug("Retrying ping to %s in %d seconds", self.base_url, delay)
            await asyncio.sleep(delay)

        _log.error("Service %s did not become ready after %d attempts", self.base_url, max_retries)
        raise TimeoutError(f"Service {self.base_url} did not become ready after {max_retries} attempts") from last_error
