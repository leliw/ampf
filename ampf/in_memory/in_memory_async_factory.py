from typing import Callable, Optional, Type

from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseAsyncStorage, BaseBlobAsyncStorage

from .in_memory_blob_async_storage import InMemoryBlobAsyncStorage
from .in_memory_storage import InMemoryStorage


class InMemoryAsyncFactory(BaseAsyncFactory):
    collections = {}

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseAsyncStorage[T]:
        if collection_name not in self.collections:
            self.collections[collection_name] = InMemoryStorage(
                collection_name=collection_name,
                clazz=clazz,
                key_name=key_name,
                key=key,
            )
        return self.collections.get(collection_name)

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], content_type: Optional[str] = None
    ) -> BaseBlobAsyncStorage[T]:
        return InMemoryBlobAsyncStorage(collection_name, clazz, content_type)
