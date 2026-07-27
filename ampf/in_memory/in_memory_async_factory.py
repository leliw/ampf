from collections.abc import Callable
from typing import ClassVar

from pydantic import BaseModel

from ampf.base import BaseAsyncBlobStorage, BaseAsyncFactory, BaseAsyncStorage, BaseBlobMetadata

from .in_memory_async_storage import InMemoryAsyncStorage
from .in_memory_blob_async_storage import InMemoryBlobAsyncStorage
from .in_memory_storage import InMemoryStorage


class InMemoryAsyncFactory(BaseAsyncFactory):
    collections: ClassVar[dict[str, InMemoryStorage]] = {}

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key_name: str | None = None,
        key: Callable[[T], str] | None = None,
    ) -> BaseAsyncStorage[T]:
        if collection_name not in self.__class__.collections:
            self.__class__.collections[collection_name] = InMemoryStorage[T](
                collection_name=collection_name,
                clazz=clazz,
                key_name=key_name,
                key=key,
            )
        storage = self.__class__.collections[collection_name]
        instance = InMemoryAsyncStorage(
            storage.collection_name,
            storage.clazz,
            storage.key,
            storage.embedding_field_name,
            storage.embedding_search_limit,
        )
        instance.storage = storage
        return instance

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] | None = None,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> BaseAsyncBlobStorage[T]:
        return InMemoryBlobAsyncStorage(collection_name, clazz, content_type)

    def drop(self):
        self.__class__.collections = {}
