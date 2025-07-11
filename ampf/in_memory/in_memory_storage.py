from typing import Any, Callable, Iterator, Optional, Type

from pydantic import BaseModel

from ampf.base import KeyNotExistsException
from ampf.base.base_collection_storage import BaseCollectionStorage
from ampf.base.base_query import BaseQuery


class InMemoryStorage[T: BaseModel](BaseCollectionStorage, BaseQuery):
    """In memory storage implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ):
        BaseCollectionStorage.__init__(self, collection_name, clazz, key_name, key)
        BaseQuery.__init__(self, self.get_all)
        self.items = {}

    def put(self, key: Any, value: T) -> None:
        self.items[str(key)] = value.model_copy(deep=True)

    def get(self, key: Any) -> T:
        ret = self.items.get(str(key))
        if ret:
            return ret.model_copy(deep=True)
        else:
            raise KeyNotExistsException(self.collection_name, self.clazz, key)

    def keys(self) -> Iterator[T]:
        for key in self.items.keys():
            yield key

    def delete(self, key: Any) -> None:
        self.items.pop(str(key), None)

    def is_empty(self) -> bool:
        return not bool(self.items)

    def drop(self):
        self.items = {}
