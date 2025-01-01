import logging
import os
from typing import Any, Optional
from pydantic import BaseModel
import requests
import jwt

from cryptography.x509 import load_pem_x509_certificate


GOOGLE_URL_PUBLIC_KEYS = "https://www.googleapis.com/oauth2/v1/certs"


class UserData(BaseModel):
    email: str
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None


class GoogleOAuth:
    """Google OAuth2 class."""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        client_id: str = None,
    ):
        self.client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", client_id)
        self._google_public_keys = self._get_google_public_keys()

    def _get_google_public_keys(self) -> None:
        """Fetches and stores Google public keys."""
        try:
            r = requests.get(GOOGLE_URL_PUBLIC_KEYS)
            r.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return r.json()
        except requests.exceptions.RequestException as e:
            self._log.error(f"Error fetching Google public keys: {e}")

    def verify_jwt(self, token: str) -> dict[str, Any] | None:
        """Verify Google JWT token and return decoded token."""
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            self._log.warning(kid)

            if not kid or kid not in self._google_public_keys:
                self._log.warning("Invalid or missing kid in JWT header")
                raise jwt.PyJWTError("Invalid or missing kid in JWT header")

            certificate = self._google_public_keys[kid]
            cert_obj = load_pem_x509_certificate(certificate.encode())
            public_key = cert_obj.public_key()
            decoded_token = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={"verify_signature": True},
            )
            decoded_token["email"] = decoded_token["email"].lower()
            return decoded_token
        except (jwt.PyJWTError, requests.exceptions.RequestException) as e:
            self._log.warning(f"Error verifying JWT: {e}")
            raise e
