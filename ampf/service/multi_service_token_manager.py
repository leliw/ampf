import asyncio

from .service_token_manager import ServiceTokenManager


class MultiServiceTokenManager():
    """Manages identity tokens for multiple services.

    This class is a factory for token managers for different service URLs.
    It ensures that for each URL, a single token manager instance is created
    and reused.
    """

    def __init__(self, token_manager_class: type[ServiceTokenManager]):
        """Initializes the MultiServiceTokenManager."""
        self.managers = {}
        self._lock = asyncio.Lock()
        self._token_manager_class = token_manager_class

    def get_token_for(self, url: str) -> str:
        """Synchronously gets an identity token for a given service URL.

        If a token manager for the URL does not exist, it will be created.

        Args:
            url: The service URL for which to get an identity token.

        Returns:
            The identity token as a string.
        """
        if url not in self.managers:
            self.managers[url] = self._token_manager_class(url)
        return self.managers[url].get_token()

    async def get_token_for_async(self, url: str) -> str:
        """Asynchronously gets an identity token for a given service URL.

        If a token manager for the URL does not exist, it will be created in a
        thread-safe way.

        Args:
            url: The service URL for which to get an identity token.

        Returns:
            The identity token as a string.
        """
        if url not in self.managers:
            async with self._lock:
                if url not in self.managers:
                    self.managers[url] = self._token_manager_class(url)
        return await self.managers[url].get_token_async()
