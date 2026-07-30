from collections.abc import Callable
from typing import override

from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseBlobMetadata

from .in_memory_async_storage import InMemoryAsyncStorage
from .in_memory_blob_async_storage import InMemoryAsyncBlobStorage
from .in_memory_factory import InMemoryFactory
from .pubsub.in_memory_topic import InMemoryTopic


class InMemoryAsyncFactory(BaseAsyncFactory):
    def __init__(self, sync_factory: InMemoryFactory | None = None):
        super().__init__()
        self.sync_factory = sync_factory or InMemoryFactory()
        self._collection_defs = self.sync_factory._collection_defs
        self._type_to_collection_defs = self.sync_factory._type_to_collection_defs


    def get_sync_factory(self) -> InMemoryFactory:
        return self.sync_factory

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
        clazz: type[T] = BaseBlobMetadata,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> InMemoryAsyncBlobStorage[T]:
        storage = self.sync_factory.create_blob_storage(collection_name, clazz, content_type, bucket_name)
        return InMemoryAsyncBlobStorage(storage)

    def drop(self):
        self.sync_factory.drop()

    @override
    def create_topic(self, topic_id: str) -> InMemoryTopic[BaseModel]:
        return self.sync_factory.create_topic(topic_id)
