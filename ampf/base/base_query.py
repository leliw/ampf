from __future__ import annotations

from abc import ABC
from typing import Generator, Iterator
from pydantic import BaseModel


class BaseQuery[T: BaseModel](ABC):
    """Base query implementation"""

    def __init__(self, src: Generator[T]):
        self._src = src

    def where(self, field: str, op: str, value: str) -> BaseQuery[T]:
        """Apply a filter to the query"""
        def it():
            return (o for o in self._src() if o.__getattribute__(field) == value)

        return BaseQuery(it)

    def get_all(self) -> Iterator[T]:
        """Get all the items after applying filters"""
        return self._src()
