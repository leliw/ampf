from __future__ import annotations

from typing import Any, Callable, Literal, Optional, Type

from pydantic import BaseModel

from .base_query import OP, BaseQuery
from .base_storage import BaseStorage


class BaseQueryStorage[T: BaseModel](BaseStorage[T], BaseQuery[T]):
    """Base query storage implementation. It is a BaseStorage with a query implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        BaseStorage.__init__(
            self,
            collection_name,
            clazz,
            key=key,
            embedding_field_name=embedding_field_name,
            embedding_search_limit=embedding_search_limit,
        )
        BaseQuery.__init__(self, self.get_all, embedding_field_name, embedding_search_limit)

    def where(self, field: str, op: OP, value: Any) -> BaseQuery[T]:
        return BaseQuery.where(self, field, op, value)
