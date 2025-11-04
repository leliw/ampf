import asyncio
from typing import Awaitable, Callable, List, Optional, Type, override

from pydantic import BaseModel

from ampf.base import KeyExistsException, KeyNotExistsException
from ampf.base.base_async_blob_storage import BaseAsyncBlobStorage
from ampf.base.blob_model import Blob, BlobHeader


class InMemoryAsyncBlobStorage[T: BaseModel](BaseAsyncBlobStorage):
    buckets = {}

    def __init__(self, collection_name: str, clazz: Optional[Type[T]] = None, content_type: Optional[str] = None):
        self.collection_name = collection_name
        self.clazz = clazz
        self.content_type = content_type
        if self.collection_name not in self.buckets:
            self.buckets[self.collection_name] = {}
        self.transaction_lock = asyncio.Lock()

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        self.buckets[self.collection_name][blob.name] = blob

    @override
    async def download_async(self, key: str) -> Blob[T]:
        try:
            return self.buckets[self.collection_name][key]
        except KeyError:
            raise KeyNotExistsException(collection_name=self.collection_name, key=key, clazz=self.clazz)

    @override
    def get_metadata(self, key: str) -> Optional[T]:
        try:
            return self.buckets[self.collection_name][key].metadata
        except KeyError:
            raise KeyNotExistsException(collection_name=self.collection_name, key=key, clazz=self.clazz)
    
    @override
    def delete(self, key: str) -> None:
        if key in self.buckets[self.collection_name]:
            del self.buckets[self.collection_name][key]
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    @override
    def exists(self, key: str) -> bool:
        return key in self.buckets[self.collection_name]

    @override
    def list_blobs(self, prefix: Optional[str] = None) -> List[BlobHeader[T]]:
        blobs = []
        for name, blob in self.buckets[self.collection_name].items():
            if prefix is None or name.startswith(prefix):
                blobs.append(BlobHeader(name=name, content_type=blob.content_type, metadata=blob.metadata))
        return blobs

    @override
    async def _upsert_transactional(
        self,
        name: str,
        create_func: Optional[Callable[[str], Awaitable[Blob[T]]]] = None,
        update_func: Optional[Callable[[Blob[T]], Awaitable[Blob[T]]]] = None,
    ) -> None:
        async with self.transaction_lock:
            try:
                blob = await self.download_async(name)
                if update_func:
                    updated_blob = await update_func(blob)
                    await self.upload_async(updated_blob)
                else:
                    raise KeyExistsException(self.collection_name, self.clazz, name)
            except KeyNotExistsException as e:
                if not create_func:
                    raise e
                created_blob = await create_func(name)
                await self.upload_async(created_blob)


# deprecated
class InMemoryBlobAsyncStorage[T: BaseModel](InMemoryAsyncBlobStorage[T]):
    pass
