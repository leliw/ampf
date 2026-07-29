import asyncio
from collections.abc import AsyncIterator, Coroutine
from typing import Any

from pydantic import BaseModel

from ampf.base import BaseAsyncQueryStorage
from ampf.base.exceptions import KeyNotExistsException
from ampf.in_memory.in_memory_storage import InMemoryStorage


class InMemoryAsyncStorage[T: BaseModel](BaseAsyncQueryStorage):
    def __init__(self, storage: InMemoryStorage[T]):
        super().__init__(
            storage.collection_name,
            storage.clazz,
            storage.key,
            storage.embedding_field_name,
            storage.embedding_search_limit,
        )
        self.storage = storage
        self.storage.to_storage = self._to_storage
        self.storage.from_storage = self._from_storage

    async def put(self, key: str, value: T) -> None:
        self.storage.put(key, value)

    async def get(self, key: str) -> T:
        if not self.storage.key_exists(key):
            raise KeyNotExistsException(self.collection_name, self.clazz, key)
        ret = self.storage.get(key)
        if isinstance(ret, Coroutine):
            ret = await ret
        return ret  # type: ignore

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

    def _to_storage(self, data: T) -> dict[str, Any]:
        ret = self.to_storage(data)
        if isinstance(ret, Coroutine):
            ret = asyncio.run(ret)
        return ret

    def _from_storage(self, data: dict[str, Any]) -> T:
        return self.from_storage(data)  # type: ignore
