from typing import List, Optional, Type, override

from pydantic import BaseModel

from ampf.base.base_blob_async_storage import BaseBlobAsyncStorage
from ampf.base.blob_model import Blob, BlobHeader


class InMemoryBlobAsyncStorage[T: BaseModel](BaseBlobAsyncStorage):
    buckets = {}

    def __init__(
        self, collection_name: str, clazz: Type[T], content_type: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        self.content_type = content_type
        if self.collection_name not in self.buckets:
            self.buckets[self.collection_name] = {}

    @override
    async def upload_async(self, blob: Blob[T]) -> None:
        self.buckets[self.collection_name][blob.name] = blob

    @override
    async def download_async(self, key: str) -> Blob[T]:
        return self.buckets[self.collection_name][key]

    @override
    def delete(self, key: str) -> None:
        if key in self.buckets[self.collection_name]:
            del self.buckets[self.collection_name][key]

    @override
    def exists(self, key: str) -> bool:
        return key in self.buckets[self.collection_name]

    @override
    def list_blobs(self, prefix: Optional[str] = None) -> List[BlobHeader[T]]:
        blobs = []
        for name, blob in self.buckets[self.collection_name].items():
            if prefix is None or name.startswith(prefix):
                blobs.append(
                    BlobHeader(
                        name=name, content_type=blob.content_type, metadata=blob.metadata
                    )
                )
        return blobs
