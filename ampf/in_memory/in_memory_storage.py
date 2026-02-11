from typing import Any, Callable, Dict, Iterator, Optional, Type

from pydantic import BaseModel

from ampf.base import KeyNotExistsException
from ampf.base.base_query_storage import BaseQueryStorage


class InMemoryStorage[T: BaseModel](BaseQueryStorage[T]):
    """In memory storage implementation"""

    _items: Dict[str, Dict[str, Dict]] = {}

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ):
        super().__init__(collection_name, clazz, key or key_name)
        if self.collection_name not in self.__class__._items:
            self.__class__._items[self.collection_name] = {}

    @property
    def items(self) -> Dict[str, Dict]:
        return self.__class__._items[self.collection_name]

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
        for key in self.items.keys():
            yield key

    def delete(self, key: Any) -> None:
        self.items.pop(str(key), None)

    def is_empty(self) -> bool:
        keys = list(self.keys())
        return not bool(keys)

    def drop(self):
        self.__class__._items[self.collection_name] = {}
