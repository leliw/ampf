from typing import Any, Callable, Dict, Iterator, Optional, Type

from pydantic import BaseModel

from ampf.base import KeyNotExistsException
from ampf.base.base_query_storage import BaseQueryStorage


class InMemoryStorage[T: BaseModel](BaseQueryStorage[T]):
    """In memory storage implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ):
        super().__init__(collection_name, clazz, key or key_name)
        self.items: Dict[str, T] = {}

    def put(self, key: Any, value: T) -> None:
        self.items[str(key)] = value.model_copy(deep=True)

    def get(self, key: Any) -> T:
        ret = self.items.get(str(key))
        if ret:
            return ret.model_copy(deep=True)
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[str]:
        for key in self.items.keys():
            yield key

    def delete(self, key: Any) -> None:
        self.items.pop(str(key), None)

    def is_empty(self) -> bool:
        return not bool(self.items)

    def drop(self):
        self.items = {}
