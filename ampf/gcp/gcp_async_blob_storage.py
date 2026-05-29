import asyncio
import logging
from typing import AsyncGenerator, Awaitable, Callable, Optional, Type, override

import aiohttp
import google.auth.exceptions
import google.auth.transport.requests
from google.api_core import exceptions
from google.cloud import storage

from ampf.base.base_async_blob_storage import BaseAsyncBlobStorage
from ampf.base.blob_model import BaseBlobMetadata, Blob, BlobHeader
from ampf.base.exceptions import KeyExistsException, KeyNotExistsException

from .gcp_base_blob_storage import GcpBaseBlobStorage

_log = logging.getLogger(__name__)


class GcpAsyncBlobStorage[T: BaseBlobMetadata](GcpBaseBlobStorage, BaseAsyncBlobStorage):
    chunk_size = 1024 * 1024  # 1MB

    def __init__(
        self,
        bucket_name: str,
        collection_name: Optional[str] = None,
        clazz: Type[T] = BaseBlobMetadata,
        content_type: str = "text/plain",
        storage_client: Optional[storage.Client] = None,
    ):
        BaseAsyncBlobStorage.__init__(self, collection_name, clazz, content_type)
        GcpBaseBlobStorage.__init__(self, bucket_name, collection_name, clazz, content_type, storage_client)
        self.clazz: Type[T] = clazz
        self.max_retries_per_transaction = 5

    def _get_signed_url(
        self,
        name: str,
        method: str,
        content_type: str | None = None,
        expiration: int = 3600,
        headers: dict | None = None,
        query_parameters: dict | None = None,
    ) -> str:
        """Generates a signed URL for the given key.

        Args:
            name: The name identifying the blob.
            method: The HTTP method for which the URL will be used (e.g., "GET", "PUT", "DELETE").
            content_type: The content type of the blob (optional, used for PUT requests).
            expiration: The expiration time of the signed URL in seconds (default is 3600 seconds, or 1 hour).
            headers: Additional headers to include in the signed URL (optional).
            query_parameters: Additional query parameters to include in the signed URL (optional).

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
            headers=headers,
            query_parameters=query_parameters,
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
        headers = self._prepare_metadata_headers(blob.metadata)
        signed_url = self._get_signed_url(blob.name, "PUT", headers=headers)
        async with aiohttp.ClientSession() as session:
            async with session.put(signed_url, data=blob.stream(), headers=headers) as response:
                response.raise_for_status()

    @override
    async def download_async(self, name: str) -> Blob[T]:
        """Downloads binary data based on the blob key.

        Args:
            name: The name identifying the blob to download.

        Returns:
            The downloaded blob object.
        """
        signed_url = self._get_signed_url(name, "GET")
        async with aiohttp.ClientSession() as session:
            async with session.get(signed_url) as response:
                if response.status == 404:
                    raise KeyNotExistsException(self.collection_name, self.clazz, name)
                response.raise_for_status()
                content = await response.read()
                metadata = self._parse_metadata(response)
                return Blob[T](name=name, content=content, metadata=metadata)

    @override
    async def delete_async(self, name: str) -> None:
        """Deletes a blob with the given name.

        Args:
            name: The name of the blob to delete.
        """
        signed_url = self._get_signed_url(name, "DELETE")
        async with aiohttp.ClientSession() as session:
            async with session.delete(signed_url) as response:
                if response.status == 404:
                    raise KeyNotExistsException(self.collection_name, self.clazz, name)
                response.raise_for_status()

    @override
    async def names(self, prefix: Optional[str] = None) -> AsyncGenerator[str]:
        prefix = self.get_full_name(prefix or "")
        col_name_len = len(self.collection_name) + 1 if self.collection_name else 0
        for blob in self._bucket.list_blobs(prefix=prefix):
            yield blob.name[col_name_len:]

    @override
    async def list_blobs(self, prefix: Optional[str] = None) -> AsyncGenerator[BlobHeader[T]]:
        """Returns a list of blob headers, optionally filtered by a prefix.

        Args:
            prefix: The prefix to filter the blobs by.

        Returns:
            A list of blob headers.
        """
        prefix = self.get_full_name(prefix or "")
        col_name_len = len(self.collection_name) + 1 if self.collection_name else 0
        for blob in self._bucket.list_blobs(prefix=prefix):
            try:
                metadata = self.clazz.model_validate(blob.metadata, extra="ignore")
                metadata.content_type = blob.content_type
                metadata.generation = blob.generation
                yield BlobHeader(name=blob.name[col_name_len:], metadata=metadata)
            except Exception as e:
                _log.warning("Failed to parse metadata for blob '%s': %s", blob.name, e)

    @override
    async def _upsert_transactional(
        self,
        name: str,
        create_func: Callable[[str], Awaitable[Blob[T]]],
        update_func: Callable[[Blob[T]], Awaitable[Blob[T]]],
    ) -> None:
        for attempt in range(self.max_retries_per_transaction):
            try:
                try:
                    blob = await self.download_async(name)
                    generation_to_match = blob.metadata.generation
                    if generation_to_match is None:
                        raise RuntimeError("Generation not found in metadata")
                    if update_func:
                        # Apply the user-defined update/creation logic
                        new_blob = await update_func(blob)
                    else:
                        raise KeyExistsException(self.collection_name, self.clazz, name)
                except (exceptions.NotFound, KeyNotExistsException):
                    if not create_func:
                        raise KeyNotExistsException(self.collection_name, self.clazz, name)
                    # Blob does not exist, prepare to create it
                    generation_to_match = 0
                    new_blob = await create_func(name)

                # Perform the conditional upload
                headers = self._prepare_metadata_headers(new_blob.metadata)
                query_parameters = {"ifGenerationMatch": str(generation_to_match)}
                # According to documentation it should be query parameter but header works !!!
                headers["x-goog-if-generation-match"] = str(generation_to_match)
                signed_url = self._get_signed_url(
                    new_blob.name, "PUT", headers=headers, query_parameters=query_parameters
                )
                async with aiohttp.ClientSession() as session:
                    async with session.put(signed_url, data=new_blob.stream(), headers=headers) as response:
                        if response.status == 412:
                            raise exceptions.PreconditionFailed(response.reason)
                        response.raise_for_status()

                return  # Success

            except exceptions.PreconditionFailed as e:
                _log.warning(
                    f"Precondition failed on attempt {attempt + 1} for blob '{name}', generation: {generation_to_match}. Retrying..."
                )
                if attempt == self.max_retries_per_transaction - 1:
                    raise e  # Re-raise after the last attempt
                await asyncio.sleep(0.1 * (2**attempt))  # Exponential backoff

    async def put_metadata(self, name: str, metadata: T) -> None:
        """Puts metadata for a blob.

        Args:
            name: The name of the blob.
            metadata: The metadata to put.
        """
        blob = self._get_blob(name)
        blob.metadata = metadata.model_dump()
        blob.patch()

    async def get_metadata(self, name: str) -> T:
        """Gets metadata for a blob.

        Args:
            name: The name of the blob.

        Returns:
            The metadata of the blob.
        """
        signed_url = self._get_signed_url(name, "GET")
        async with aiohttp.ClientSession() as session:
            async with session.head(signed_url) as response:
                if response.status == 404:
                    raise KeyNotExistsException(self.collection_name, self.clazz, name)
                response.raise_for_status()
                return self._parse_metadata(response)

    def _parse_metadata(self, response: aiohttp.ClientResponse) -> T:
        headers_dict = dict(response.headers)
        metadata = {}
        for key, value in headers_dict.items():
            if key.startswith("x-goog-meta-"):
                metadata[key.replace("x-goog-meta-", "")] = value
            else:
                match key:
                    case "Content-Type":
                        metadata["content_type"] = value
                    case "x-goog-generation":
                        metadata["generation"] = int(value)
                    case _:
                        pass
        return self.clazz.model_validate(metadata, extra="ignore")

    def _prepare_metadata_headers(self, metadata: T | None = None) -> dict:
        if metadata:
            headers = {}
            for key, value in metadata.model_dump(exclude_unset=True, by_alias=False).items():
                match key:
                    case "content_type":
                        headers["Content-Type"] = str(value)
                    case "generation":
                        headers["x-goog-generation"] = str(value)
                    case _:
                        headers[f"x-goog-meta-{key}"] = str(value)
        else:
            headers = {"Content-Type": self.content_type}
        return headers
