from collections.abc import Callable
from typing import override

from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseBlobMetadata

from .in_memory_async_storage import InMemoryAsyncStorage
from .in_memory_blob_async_storage import InMemoryBlobAsyncStorage
from .in_memory_factory import InMemoryFactory
from .in_memory_storage import InMemoryStorage
from .pubsub.in_memory_topic import InMemoryTopic


class InMemoryAsyncFactory(BaseAsyncFactory):
    def __init__(self, sync_factory: InMemoryFactory | None = None):
        super().__init__()
        self.sync_factory = sync_factory or InMemoryFactory()

    @property
    def collections(self) -> dict[str, InMemoryStorage]:
        return self.sync_factory.collections

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ) -> InMemoryAsyncStorage[T]:
        storage = self.sync_factory.create_storage(collection_name, clazz, key)
        instance = InMemoryAsyncStorage(storage)
        return instance

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] | None = None,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> InMemoryBlobAsyncStorage[T]:
        return InMemoryBlobAsyncStorage(collection_name, clazz, content_type)

    def drop(self):
        self.sync_factory.drop()

    @override
    def create_topic(self, topic_id: str) -> InMemoryTopic[BaseModel]:
        return InMemoryTopic(topic_id)
