from collections.abc import Callable
from copy import copy
from typing import Any, override

from pydantic import BaseModel

from ampf.base import BaseBlobMetadata, BaseFactory
from ampf.base.blob_model import Blob
from ampf.base.collection_def import CollectionDef

from .in_memory_blob_storage import InMemoryBlobStorage
from .in_memory_storage import InMemoryStorage
from .pubsub.in_memory_registry import InMemoryPubsubRegistry
from .pubsub.in_memory_topic import InMemoryTopic


class InMemoryFactory(BaseFactory):
    def __init__(self, collection_defs: list[CollectionDef[Any]] | None = None):
        super().__init__(collection_defs)
        self.collections: dict[str, InMemoryStorage] = {}
        self.buckets: dict[str, dict[str, Blob]] = {}
        self.pubsub_registry = InMemoryPubsubRegistry()

    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ) -> InMemoryStorage[T]:
        if collection_name not in self.collections:
            collection_name = collection_name.rstrip("/") if collection_name else ""
            self.collections[collection_name] = InMemoryStorage[T](
                collection_name=collection_name, clazz=clazz, key=key
            )
        ret = self.collections[collection_name]
        if ret.clazz is not clazz:
            # Different class, so I return shallow copy with desired class
            ret = copy(ret)
            ret.clazz = clazz
        return ret

    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str,
        clazz: type[T] = BaseBlobMetadata,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> InMemoryBlobStorage[T]:
        bucket_name = bucket_name or "__default__"
        if bucket_name not in self.buckets:
            self.buckets[bucket_name] = {}
        return InMemoryBlobStorage[T](bucket_name, self.buckets[bucket_name], collection_name, clazz, content_type)

    def drop(self):
        self.collections = {}

    @override
    def create_topic(self, topic_id: str) -> InMemoryTopic[BaseModel]:
        return InMemoryTopic(self.pubsub_registry, topic_id)
