import asyncio
import logging
import time

from google.auth import jwt
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from ampf.service.service_token_manager import ServiceTokenManager

_log = logging.getLogger(__name__)


class GoogleIDTokenManager(ServiceTokenManager):
    """A utility class to manage and refresh Google ID tokens for a given audience.

    It caches tokens and refreshes them before they expire to minimize API calls.
    """

    def __init__(self, audience: str):
        """
        Initializes the Google ID token manager.

        Args:
            audience (str): The audience (url) for which the token is requested.
        """
        self.audience = audience
        self._token = None
        self._expiry = 0
        self._lock = asyncio.Lock()
        self._auth_req = Request()

    def get_token(self) -> str:
        """Retrieves a Google ID token, using a cached token if available and not expired.

        Tokens are refreshed if they are within 5 minutes of expiration.

        Returns:
            str: The Google ID token.
        """
        current_time = time.time()
        if self._token and current_time < (self._expiry - 300):
            return self._token
        current_time = time.time()
        if self._token and current_time < (self._expiry - 300):
            return self._token
        try:
            _log.debug("Getting token for %s", self.audience)
            new_token = id_token.fetch_id_token(self._auth_req, self.audience)
            decoded = jwt.decode(new_token, verify=False)
            self._token = new_token
            self._expiry = decoded["exp"]
            _log.debug("Token received for %s", self.audience)
            _log.debug("Token expires at %d seconds from now", int(self._expiry - current_time))
            if self._token:
                return self._token
            raise Exception("No token received")
        except Exception as e:
            _log.exception("Error getting token: %s", e)
            raise

    def get_token_for(self, url: str) -> str:
        if self.audience != url:
            raise Exception("Audience mismatch")
        return self.get_token()

    async def get_token_async(self) -> str:
        """Retrieves a Google ID token, using a cached token if available and not expired.

        Tokens are refreshed if they are within 5 minutes of expiration.

        Returns:
            str: The Google ID token.
        """
        current_time = time.time()
        if self._token and current_time < (self._expiry - 300):
            return self._token
        async with self._lock:
            current_time = time.time()
            if self._token and current_time < (self._expiry - 300):
                return self._token
            try:
                _log.debug("Getting token for %s", self.audience)
                new_token = await asyncio.to_thread(id_token.fetch_id_token, self._auth_req, self.audience)
                decoded = jwt.decode(new_token, verify=False)
                self._token = new_token
                self._expiry = decoded["exp"]
                _log.debug("Token received for %s", self.audience)
                _log.debug("Token expires at %d seconds from now", int(self._expiry - current_time))
                if self._token:
                    return self._token
                raise Exception("No token received")
            except Exception as e:
                _log.exception("Error getting token: %s", e)
                raise

    async def get_token_for_async(self, url: str) -> str:
        if self.audience != url:
            raise Exception("Audience mismatch")
        return await self.get_token_async()
