from typing import AsyncIterator, Type
from pydantic import BaseModel
from ampf.base import BaseAsyncStorage
from ampf.in_memory.in_memory_storage import InMemoryStorage


class InMemoryAsyncStorage[T: BaseModel](BaseAsyncStorage):
    def __init__(self, collection_name: str, clazz: Type[T], key_name: str = None):
        super().__init__(collection_name, clazz, key_name)
        self.storage = InMemoryStorage(collection_name, clazz, key_name)

    async def put(self, key: str, value: T) -> None:
        self.storage.put(key, value)

    async def get(self, key: str) -> T:
        return self.storage.get(key)

    async def keys(self) -> AsyncIterator[str]:
        for key in self.storage.keys():
            yield key
    

    async def delete(self, key: str) -> None:
        self.storage.delete(key)

    async def drop(self) -> None:
        self.storage.drop()

    async def key_exists(self, needle: str) -> bool:
        return self.storage.key_exists(needle)

    async def is_empty(self) -> bool:
        return self.storage.is_empty()
