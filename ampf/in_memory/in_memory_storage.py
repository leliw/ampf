from collections.abc import Callable, Iterator
from typing import Any

from pydantic import BaseModel

from ampf.base import KeyNotExistsException
from ampf.base.base_query_storage import BaseQueryStorage


class InMemoryStorage[T: BaseModel](BaseQueryStorage[T]):
    """In memory storage implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ):
        super().__init__(collection_name, clazz, key)
        self.items: dict[str, dict] = {}

    def put(self, key: Any, value: T) -> None:
        new_key = self.get_key(value)
        # If the key of the value has changed, remove the old key
        if str(key) != new_key and str(key) in self.items:
            self.items.pop(str(key))
        # Store the value with the new key
        self.items[str(new_key)] = self.to_storage(value)

    def get(self, key: Any) -> T:
        ret = self.items.get(str(key))
        if ret:
            return self.from_storage(ret)
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[str]:
        yield from self.items.keys()

    def delete(self, key: Any) -> None:
        self.items.pop(str(key), None)

    def is_empty(self) -> bool:
        keys = list(self.keys())
        return not bool(keys)

    def drop(self):
        self.items = {}
