from typing import Any, Callable, Dict, Iterator, Optional, Type

from pydantic import BaseModel

from ampf.base import KeyNotExistsException
from ampf.base.base_query_storage import BaseQueryStorage


class InMemoryStorage[T: BaseModel](BaseQueryStorage[T]):
    """In memory storage implementation"""

    items: Dict[str, T] = {}

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ):
        super().__init__(collection_name, clazz, key or key_name)

    def _key_to_str(self, key: Any) -> str:
        return f"{self.collection_name}/{str(key)}"

    def _key_from_str(self, s: str) -> str:
        return s[len(self.collection_name) + 1 :]

    def put(self, key: Any, value: T) -> None:
        new_key = self.get_key(value)
        # If the key of the value has changed, remove the old key
        if self._key_to_str(key) != new_key and self._key_to_str(key) in self.items:
            self.items.pop(self._key_to_str(key))
        # Store the value with the new key
        self.items[self._key_to_str(new_key)] = value.model_copy(deep=True)

    def get(self, key: Any) -> T:
        ret = self.items.get(self._key_to_str(key))
        if ret:
            if isinstance(ret, self.clazz):
                return ret.model_copy(deep=True)
            else:
                d = ret.model_dump(by_alias=True, exclude_none=True)
                return self.from_storage(d)
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[str]:
        for key in self.items.keys():
            yield self._key_from_str(key)

    def delete(self, key: Any) -> None:
        self.items.pop(self._key_to_str(key), None)

    def is_empty(self) -> bool:
        return not bool(self.items)

    def drop(self):
        self.__class__.items = {}
