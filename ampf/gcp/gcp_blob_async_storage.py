import logging
from typing import Optional, Type, override

import aiohttp
from google.cloud.storage.client import Client as StorageClient
from pydantic import BaseModel

from ampf.base.base_blob_async_storage import BaseBlobAsyncStorage
from ampf.base.blob_model import Blob

from .gcp_base_blob_storage import GcpBaseBlobStorage


class GcpBlobAsyncStorage[T: BaseModel](GcpBaseBlobStorage, BaseBlobAsyncStorage):
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        bucket_name: str,
        collection_name: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        content_type: str = "text/plain",
        storage_client: Optional[StorageClient] = None,
    ):
        BaseBlobAsyncStorage.__init__(self, collection_name, clazz, content_type)
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
        blob = self._get_blob(name)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method=method,
            content_type=content_type,
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
