from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from .base_async_query import BaseAsyncQuery
from .base_async_storage import BaseAsyncStorage
from .base_query import OP


class BaseAsyncQueryStorage[T: BaseModel](BaseAsyncStorage[T], BaseAsyncQuery[T]):
    """Base query storage implementation. It is a BaseStorage with a query implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        BaseAsyncStorage.__init__(self, collection_name, clazz, key, embedding_field_name, embedding_search_limit)
        BaseAsyncQuery.__init__(self, self.get_all, embedding_field_name, embedding_search_limit)

    def where(self, field: str, op: OP, value: Any) -> BaseAsyncQuery[T]:
        return BaseAsyncQuery.where(self, field, op, value)
