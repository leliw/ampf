from __future__ import annotations

from typing import Callable, Optional, Type

from pydantic import BaseModel

from ampf.base.base_query import BaseQuery
from ampf.base.base_storage import BaseStorage


class BaseQueryStorage[T: BaseModel](BaseStorage[T], BaseQuery[T]):
    """Base query storage implementation. It is a BaseStorage with a query implementation"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
    ):
        BaseStorage.__init__(self, collection_name, clazz, key = key)
        BaseQuery.__init__(self, self.get_all)
