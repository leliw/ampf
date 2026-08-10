import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import override
from warnings import deprecated

from ampf.base import KeyExistsException, KeyNotExistsException
from ampf.base.base_async_blob_storage import BaseAsyncBlobStorage
from ampf.base.blob_model import BaseBlobMetadata, Blob, BlobHeader
from ampf.in_memory.in_memory_blob_storage import InMemoryBlobStorage


class InMemoryAsyncBlobStorage[T: BaseBlobMetadata](BaseAsyncBlobStorage):
    def __init__(self, storage: InMemoryBlobStorage):
        self.storage = storage
        super().__init__(
            collection_name=storage.collection_name, clazz=storage.clazz, content_type=storage.content_type
        )
        self.transaction_lock = asyncio.Lock()

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        self.storage.upload(blob)

    @override
    async def download_async(self, key: str) -> Blob[T]:
        return self.storage.download(key)

    @override
    async def get_metadata(self, key: str) -> T:
        return self.storage.get_metadata(key)

    @override
    async def put_metadata(self, key: str, metadata: T) -> None:
        self.storage.put_metadata(key, metadata)

    @override
    def delete(self, key: str) -> None:
        self.storage.delete(key)

    @override
    def exists(self, key: str) -> bool:
        return self.storage.exists(key)

    @override
    async def names(self, prefix: str | None = None) -> AsyncGenerator[str]:
        prefix = prefix.rstrip("/") + "/" if prefix else ""
        for k in self.storage:
            if k.startswith(prefix):
                blob = self.storage.download(k)
                yield blob.name

    @override
    async def list_blobs(self, prefix: str | None = None) -> AsyncGenerator[BlobHeader[T]]:
        prefix = prefix.rstrip("/") + "/" if prefix else ""
        for k in self.storage:
            if k.startswith(prefix):
                blob = self.storage.download(k)
                yield BlobHeader(name=blob.name, metadata=blob.metadata)

    @override
    async def _upsert_transactional(
        self,
        name: str,
        create_func: Callable[[str], Awaitable[Blob[T]]] | None = None,
        update_func: Callable[[Blob[T]], Awaitable[Blob[T]]] | None = None,
    ) -> None:
        async with self.transaction_lock:
            try:
                blob = await self.download_async(name)
                if update_func:
                    updated_blob = await update_func(blob)
                    await self.upload_async(updated_blob)
                else:
                    raise KeyExistsException(self.collection_name, self.clazz, name)
            except KeyNotExistsException:
                if not create_func:
                    raise
                created_blob = await create_func(name)
                await self.upload_async(created_blob)


@deprecated("Use InMemoryAsyncBlobStorage")
class InMemoryBlobAsyncStorage[T: BaseBlobMetadata](InMemoryAsyncBlobStorage[T]):
    pass
