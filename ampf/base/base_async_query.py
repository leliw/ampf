from __future__ import annotations

from abc import ABC
from typing import Any, AsyncIterator, Callable, Self

from pydantic import BaseModel
from typing_extensions import Literal


class BaseAsyncQuery[T: BaseModel](ABC):
    """Base query with a defalt, brute force implementation."""

    def __init__(self, src: Callable[[], AsyncIterator[T]]):
        self._src = src

    def where(self, field: str, op: Literal["==", "!=", "<", "<=", ">", ">="], value: Any) -> BaseAsyncQuery[T]:
        """Apply a filter to the query"""
        # The inner function `it` is an async generator that will be the new source for the next query object.
        # It wraps the original source (`src`) and applies the filter.
        async def it(src=self._src) -> AsyncIterator[T]:
            # Iterate asynchronously over the items from the source.
            async for o in src():
                # Get the attribute from the object.
                attr = getattr(o, field)
                # Match the operator and apply the corresponding comparison.
                match op:
                    case "==":
                        if attr == value:
                            yield o
                    case "!=":
                        if attr != value:
                            yield o
                    case "<":
                        if attr < value:
                            yield o
                    case "<=":
                        if attr <= value:
                            yield o
                    case ">":
                        if attr > value:
                            yield o
                    case ">=":
                        if attr >= value:
                            yield o

        return BaseAsyncQuery(it)

    async def get_all(self) -> AsyncIterator[T]:
        """Get all the items after applying filters"""
        # Asynchronously iterate over the source and yield each item.
        # This makes get_all an async generator itself.
        async for item in self._src():
            yield item
