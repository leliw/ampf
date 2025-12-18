from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseAsyncStorage, BaseAsyncBlobStorage
from .in_memory_async_storage import InMemoryAsyncStorage

from .in_memory_blob_async_storage import InMemoryBlobAsyncStorage


class InMemoryAsyncFactory(BaseAsyncFactory):
    collections: Dict[str, InMemoryAsyncStorage] = {}

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseAsyncStorage[T]:
        if collection_name not in self.collections:
            self.collections[collection_name] = InMemoryAsyncStorage(
                collection_name=collection_name,
                clazz=clazz,
                key=key or key_name,
            )
        return self.collections.get(collection_name)  # type: ignore

    def create_blob_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> BaseAsyncBlobStorage[T]:
        return InMemoryBlobAsyncStorage(collection_name, clazz, content_type)
