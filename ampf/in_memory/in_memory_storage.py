from typing import Iterator, Type
from pydantic import BaseModel
from ampf.base import BaseStorage, KeyNotExistsException


class InMemoryStorage[T: BaseModel](BaseStorage):
    """In memory storage implementation"""

    def __init__(self, collection_name: str, clazz: Type[T], key_name: str = None):
        super().__init__(collection_name, clazz, key_name)
        self.items = {}

    def put(self, key: str, value: T) -> None:
        self.items[key] = value.model_copy(deep=True)

    def get(self, key: str) -> T:
        ret = self.items.get(key)
        if ret:
            return ret.model_copy(deep=True)
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[T]:
        return self.items.keys()

    def delete(self, key: str) -> None:
        self.items.pop(key, None)

    def is_empty(self) -> bool:
        return not bool(self.items)

    def drop(self):
        self.items = {}
