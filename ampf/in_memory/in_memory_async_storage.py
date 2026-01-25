from typing import AsyncIterator, Callable, Optional, Type

from pydantic import BaseModel

from ampf.base import BaseAsyncQueryStorage
from ampf.base.exceptions import KeyNotExistsException
from ampf.in_memory.in_memory_storage import InMemoryStorage


class InMemoryAsyncStorage[T: BaseModel](BaseAsyncQueryStorage):
    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        super().__init__(collection_name, clazz, key, embedding_field_name, embedding_search_limit)
        self.storage = InMemoryStorage(
            collection_name,
            clazz,
            key_name=key if isinstance(key, str) else None,
            key=key if isinstance(key, Callable) else None,
        )

    @classmethod
    def create(cls, storage: InMemoryStorage):
        instance = cls(
            storage.collection_name,
            storage.clazz,
            storage.key,
            storage.embedding_field_name,
            storage.embedding_search_limit,
        )
        instance.storage = storage
        return instance

    async def put(self, key: str, value: T) -> None:
        self.storage.put(key, value)

    async def get(self, key: str) -> T:
        if not self.storage.key_exists(key):
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        return self.storage.get(key)

    async def keys(self) -> AsyncIterator[str]:
        for key in self.storage.keys():
            yield key

    async def delete(self, key: str) -> None:
        if not self.storage.key_exists(key):
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        self.storage.delete(key)

    async def drop(self) -> None:
        self.storage.drop()

    async def key_exists(self, needle: str) -> bool:
        return self.storage.key_exists(needle)

    async def is_empty(self) -> bool:
        return self.storage.is_empty()
