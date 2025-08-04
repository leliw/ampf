import logging
from typing import Iterable, List, Optional, Type, override

import aiohttp
from google.cloud import storage
from google.cloud.storage.client import Client as StorageClient
from pydantic import BaseModel

from ampf.base.base_blob_async_storage import BaseBlobAsyncStorage
from ampf.base.blob_model import Blob, BlobHeader
from ampf.base.exceptions import KeyNotExistsException


class GcpBlobAsyncStorage[T: BaseModel](BaseBlobAsyncStorage):
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        bucket_name: str,
        collection_name: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        content_type: str = "text/plain",
        storage_client: Optional[StorageClient] = None,
    ):
        super().__init__(collection_name, clazz, content_type)
        self.bucket_name = bucket_name
        self._storage_client = storage_client or storage.Client()
        if bucket_name:
            self._bucket = self._storage_client.bucket(bucket_name)
        else:
            raise ValueError(
                f"No bucket specified or found for collection '{collection_name}'. Please provide a valid bucket_name."
            )

    def _get_signed_url(self, name: str, method: str, content_type: Optional[str] = None, expiration: int = 3600) -> str:
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
        metadata = self.get_metadata(name)
        signed_url = self._get_signed_url(name, "GET")

        async with aiohttp.ClientSession() as session:
            async with session.get(signed_url) as response:
                response.raise_for_status()
                data = await response.read()

        return Blob(name=name, data=data, content_type=response.content_type, metadata=metadata)


    @override
    def delete(self, name: str) -> None:
        blob = self._get_blob(name)
        blob.delete()


    @override
    def exists(self, key: str) -> bool:
        pass

    @override
    def list_blobs(self, prefix: Optional[str] = None) -> Iterable[BlobHeader[T]]:
        if self.collection_name:
            prefix = f"{self.collection_name}/{prefix or ""}"
        else:
            prefix = ""
        col_name_len = len(self.collection_name) + 1 if self.collection_name else 0
        for blob in self._bucket.list_blobs(prefix=prefix):
            yield BlobHeader(
                name=blob.name[col_name_len:],
                content_type=blob.content_type,
                metadata=self.clazz(**blob.metadata) if self.clazz and blob.metadata else None,
            )

    def _get_blob(self, name: str) -> storage.Blob:
        return self._bucket.blob(f"{self.collection_name}/{name}" if self.collection_name else name)

    def put_metadata(self, name: str, metadata: T) -> None:
        blob = self._get_blob(name)
        blob.metadata = metadata.model_dump()
        blob.patch()

    def get_metadata(self, name: str) -> Optional[T]:
        blob = self._get_blob(name)
        if not blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, name)
        if not blob.metadata:
            # I don't know why, but sometimes the metadata is None (ML)
            blob.reload()
        if not blob.metadata or not self.clazz:
            return None
        return self.clazz(**blob.metadata)
