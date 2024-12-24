from typing import Type
from pydantic import BaseModel

from ampf.base import BaseFactory, BaseStorage
from ampf.in_memory import InMemoryStorage


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
