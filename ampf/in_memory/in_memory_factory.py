from collections.abc import Callable
from typing import ClassVar, override

from pydantic import BaseModel

from ampf.base import BaseFactory, BaseStorage
from ampf.base.base_blob_storage import BaseBlobStorage
from ampf.base.base_topic import BaseTopic
from ampf.base.blob_model import BaseBlobMetadata
from ampf.in_memory.pubsub.in_memory_topic import InMemoryTopic

from .in_memory_blob_storage import InMemoryBlobStorage
from .in_memory_storage import InMemoryStorage


class InMemoryFactory(BaseFactory):
    collections: ClassVar[dict[str, InMemoryStorage]] = {}

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key_name: str | None = None,
        key: Callable[[T], str] | None = None,
    ) -> BaseStorage[T]:
        if collection_name not in self.collections:
            self.collections[collection_name] = InMemoryStorage(
                collection_name=collection_name,
                clazz=clazz,
                key_name=key_name,
                key=key,
            )
        return self.collections.get(collection_name)  # type: ignore

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] | None = None,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> BaseBlobStorage[T]:
        return InMemoryBlobStorage(collection_name, clazz, content_type)

    @override
    def create_topic(self, topic_id: str) -> BaseTopic[BaseModel]:
        return InMemoryTopic(topic_id)
