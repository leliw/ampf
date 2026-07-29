from collections.abc import Callable
from typing import override

from pydantic import BaseModel

from ampf.base import BaseBlobMetadata, BaseBlobStorage, BaseFactory, BaseStorage

from .in_memory_blob_storage import InMemoryBlobStorage
from .in_memory_storage import InMemoryStorage
from .pubsub.in_memory_topic import InMemoryTopic


class InMemoryFactory(BaseFactory):
    def __init__(self):
        self.collections: dict[str, InMemoryStorage] = {}
        # self.buckets: dict[str, dict[str, bytes]] = {}

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key_name: str | None = None,
        key: Callable[[T], str] | None = None,
    ) -> BaseStorage[T]:
        if collection_name not in self.collections:
            self.collections[collection_name] = InMemoryStorage[T](
                collection_name=collection_name,
                clazz=clazz,
                key_name=key_name,
                key=key,
            )
        return self.collections[collection_name]

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] | None = None,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> BaseBlobStorage[T]:
        return InMemoryBlobStorage(collection_name, clazz, content_type)

    def drop(self):
        self.collections = {}

    @override
    def create_topic(self, topic_id: str) -> InMemoryTopic[BaseModel]:
        return InMemoryTopic(topic_id)
