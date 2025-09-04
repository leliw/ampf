from __future__ import annotations

from typing import Callable, Optional, Type

from pydantic import BaseModel

from ampf.base.base_async_query import BaseAsyncQuery
from ampf.base.base_async_storage import BaseAsyncStorage


class BaseAsyncQueryStorage[T: BaseModel](BaseAsyncStorage[T], BaseAsyncQuery[T]):
    """Base query storage implementation. It is a BaseStorage with a query implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        BaseAsyncStorage.__init__(self, collection_name, clazz, key, embedding_field_name, embedding_search_limit)
        BaseAsyncQuery.__init__(self, self.get_all)
