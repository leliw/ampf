from typing import Callable, Iterator, Type

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
        key_name: str = None,
        key: Callable[[T], str] = None,
    ):
        BaseCollectionStorage.__init__(self, collection_name, clazz, key_name, key)
        BaseQuery.__init__(self, self.get_all)
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
        for key in self.items.keys():
            yield key

    def delete(self, key: str) -> None:
        self.items.pop(key, None)

    def is_empty(self) -> bool:
        return not bool(self.items)

    def drop(self):
        self.items = {}
