import asyncio
import logging
from typing import Awaitable, Callable, Optional, Type, override

import aiohttp
import google.auth.exceptions
import google.auth.transport.requests
from google.api_core import exceptions
from google.cloud import storage
from pydantic import BaseModel

from ampf.base.base_async_blob_storage import BaseAsyncBlobStorage
from ampf.base.blob_model import Blob
from ampf.base.exceptions import KeyNotExistsException

from .gcp_base_blob_storage import GcpBaseBlobStorage


class GcpAsyncBlobStorage[T: BaseModel](GcpBaseBlobStorage, BaseAsyncBlobStorage):
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        bucket_name: str,
        collection_name: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        content_type: str = "text/plain",
        storage_client: Optional[storage.Client] = None,
    ):
        BaseAsyncBlobStorage.__init__(self, collection_name, clazz, content_type)
        GcpBaseBlobStorage.__init__(self, bucket_name, collection_name, clazz, content_type, storage_client)

    def _get_signed_url(
        self, name: str, method: str, content_type: Optional[str] = None, expiration: int = 3600
    ) -> str:
        """Generates a signed URL for the given key.

        Args:
            key: The key for which to generate the signed URL.
            expiration: The expiration time in seconds.

        Returns:
            The signed URL.
        """
        try:
            creds, _ = google.auth.default()
            creds.refresh(google.auth.transport.requests.Request()) # type: ignore
        except google.auth.exceptions.RefreshError:
            creds = None

        blob = self._get_blob(name)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method=method,
            content_type=content_type,
            service_account_email=creds.service_account_email if creds else None,  # type: ignore
            access_token=creds.token if creds else None, # type: ignore
        )
        return signed_url

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        """Uploads binary data to the storage.

        Args:
            blob: The blob object containing data and metadata to upload.
        """
        contet_type = blob.content_type or self.content_type or "application/octet-stream"
        signed_url = self._get_signed_url(blob.name, "PUT", content_type=contet_type)

        async with aiohttp.ClientSession() as session:
            async with session.put(
                signed_url, data=blob.data.read(), headers={"Content-Type": contet_type}
            ) as response:
                response.raise_for_status()

        if blob.metadata:
            self.put_metadata(blob.name, blob.metadata)

    @override
    async def download_async(self, name: str) -> Blob[T]:
        """Downloads binary data based on the blob key.

        Args:
            name: The name identifying the blob to download.

        Returns:
            The downloaded blob object.
        """
        metadata = self.get_metadata(name)
        signed_url = self._get_signed_url(name, "GET")

        async with aiohttp.ClientSession() as session:
            async with session.get(signed_url) as response:
                response.raise_for_status()
                data = await response.read()

        return Blob(name=name, data=data, content_type=response.content_type, metadata=metadata)

    async def update_transactional(self, name: str, update_func: Callable[[Blob[T]], Awaitable[Blob[T]]]) -> None:
        storage_blob = self._get_blob(name)
        if not storage_blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, name)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                storage_blob = self._get_blob(name)
                data = storage_blob.download_as_bytes()
                curr_generation = storage_blob.generation
                if curr_generation is None:
                    raise exceptions.PreconditionFailed("Blob generation is None")
                content_type = storage_blob.content_type
                metadata = self.get_metadata(name)
                blob = Blob(name=name, data=data, content_type=content_type, metadata=metadata)
                updated_blob = await update_func(blob)
                storage_blob.upload_from_string(
                    updated_blob.data.read(),
                    content_type=updated_blob.content_type or self.content_type,
                    if_generation_match=curr_generation,
                )
                return
            except exceptions.PreconditionFailed as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(0.5 * (attempt + 1))

            except exceptions.NotFound:
                raise KeyNotExistsException(self.collection_name, self.clazz, name)

            except Exception as e:
                self._log.error(f"Error during transactional update of blob '{name}': {e}")
                raise e