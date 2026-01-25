from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel

from ampf.base import BaseAsyncBlobStorage, BaseAsyncFactory, BaseAsyncStorage
from ampf.base.blob_model import BaseBlobMetadata
from ampf.in_memory.in_memory_async_storage import InMemoryAsyncStorage

from .in_memory_blob_async_storage import InMemoryBlobAsyncStorage
from .in_memory_storage import InMemoryStorage


class InMemoryAsyncFactory(BaseAsyncFactory):
    collections: Dict[str, InMemoryStorage] = {}

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseAsyncStorage[T]:
        if collection_name not in self.collections:
            self.collections[collection_name] = InMemoryStorage[T](
                collection_name=collection_name,
                clazz=clazz,
                key_name=key_name,
                key=key,
            )
        return InMemoryAsyncStorage.create(self.collections.get(collection_name))  # type: ignore

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> BaseAsyncBlobStorage[T]:
        return InMemoryBlobAsyncStorage(collection_name, clazz, content_type)
