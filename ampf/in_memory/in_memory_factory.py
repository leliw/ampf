from typing import Type
from pydantic import BaseModel

from ampf.base import BaseFactory, BaseStorage
from ampf.base.base_blob_storage import BaseBlobStorage
from .in_memory_storage import InMemoryStorage
from .in_memory_blob_storage import InMemoryBlobStorage


class InMemoryFactory(BaseFactory):
    collections = {}

    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key_name: str = None
    ) -> BaseStorage[T]:
        if collection_name not in self.collections:
            self.collections[collection_name] = InMemoryStorage(
                collection_name=collection_name,
                clazz=clazz,
                key_name=key_name,
            )
        return self.collections.get(collection_name)

    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T] = None, content_type: str = None
    ) -> BaseBlobStorage[T]:
        return InMemoryBlobStorage(collection_name, clazz, content_type)