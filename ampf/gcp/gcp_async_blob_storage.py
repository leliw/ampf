import asyncio
import logging
from typing import Awaitable, Callable, Optional, Type, override

import aiohttp
import google.auth.exceptions
import google.auth.transport.requests
from google.api_core import exceptions
from google.cloud import storage

from ampf.base.base_async_blob_storage import BaseAsyncBlobStorage
from ampf.base.blob_model import BaseBlobMetadata, Blob
from ampf.base.exceptions import KeyNotExistsException, KeyExistsException

from .gcp_base_blob_storage import GcpBaseBlobStorage


class GcpAsyncBlobStorage[T: BaseBlobMetadata](GcpBaseBlobStorage, BaseAsyncBlobStorage):
    _log = logging.getLogger(__name__)
    chunk_size = 1024 * 1024  # 1MB

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
        self.max_retries_per_transaction = 5

    def _get_signed_url(self, name: str, method: str, content_type: Optional[str] = None, expiration: int = 3600) -> str:
        """Generates a signed URL for the given key.

        Args:
            key: The key for which to generate the signed URL.
            expiration: The expiration time in seconds.

        Returns:
            The signed URL.
        """
        try:
            creds, _ = google.auth.default()
            creds.refresh(google.auth.transport.requests.Request())  # type: ignore
        except google.auth.exceptions.RefreshError:
            creds = None

        blob = self._get_blob(name)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method=method,
            content_type=content_type,
            service_account_email=creds.service_account_email if creds else None,  # type: ignore
            access_token=creds.token if creds else None,  # type: ignore
        )
        return signed_url

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        """Uploads binary data to the storage.

        Args:
            blob: The blob object containing data and metadata to upload.
        """
        content_type = blob.content_type or self.content_type or "application/octet-stream"
        signed_url = self._get_signed_url(blob.name, "PUT", content_type=content_type)

        async with aiohttp.ClientSession() as session:
            async with session.put(
                signed_url, data=blob.stream(), headers={"Content-Type": content_type}
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
                content = await response.read()

        return Blob(name=name, content=content, content_type=response.content_type, metadata=metadata)

    async def _upsert_transactional(
        self,
        name: str,
        create_func: Callable[[str], Awaitable[Blob[T]]],
        update_func: Callable[[Blob[T]], Awaitable[Blob[T]]],
    ) -> None:
        for attempt in range(self.max_retries_per_transaction):
            try:
                # Try to get the blob to see if it exists and get its generation
                storage_blob = self._get_blob(name)
                try:
                    storage_blob.reload()  # Get the latest metadata, including generation
                    content = storage_blob.download_as_bytes()
                    generation_to_match = storage_blob.generation
                    content_type = storage_blob.content_type
                    metadata = self.get_metadata(name)
                    blob = Blob(name=name, content=content, content_type=content_type, metadata=metadata)
                    if update_func:
                        # Apply the user-defined update/creation logic
                        new_blob = await update_func(blob)
                    else:
                        raise KeyExistsException(self.collection_name, self.clazz, name)
                except exceptions.NotFound:
                    if not create_func:
                        raise KeyNotExistsException(self.collection_name, self.clazz, name)
                    # Blob does not exist, prepare to create it
                    generation_to_match = 0
                    new_blob = await create_func(name)

                # Perform the conditional upload
                storage_blob.upload_from_string(
                    new_blob.content,
                    content_type=new_blob.content_type or self.content_type,
                    if_generation_match=generation_to_match,
                )

                if new_blob.metadata:
                    self.put_metadata(name, new_blob.metadata)

                return  # Success

            except exceptions.PreconditionFailed as e:
                self._log.warning(f"Precondition failed on attempt {attempt + 1} for blob '{name}'. Retrying...")
                if attempt == self.max_retries_per_transaction - 1:
                    raise e  # Re-raise after the last attempt
                await asyncio.sleep(0.1 * (2**attempt))  # Exponential backoff
