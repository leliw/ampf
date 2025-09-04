from __future__ import annotations

from abc import ABC
from typing import Any, Callable, Iterator

from pydantic import BaseModel
from typing_extensions import Literal


class BaseQuery[T: BaseModel](ABC):
    """Base query with defalt, brute force implementation."""

    def __init__(self, src: Callable[[], Iterator[T]]):
        self._src = src

    def where(self, field: str, op: Literal["==", "!=", "<", "<=", ">", ">="], value: Any) -> BaseQuery[T]:
        """Apply a filter to the query"""

        def it(src=self._src):
            match op:
                case "==":
                    return (o for o in src() if o.__getattribute__(field) == value)
                case "!=":
                    return (o for o in src() if o.__getattribute__(field) != value)
                case "<":
                    return (o for o in src() if o.__getattribute__(field) < value)
                case "<=":
                    return (o for o in src() if o.__getattribute__(field) <= value)
                case ">":
                    return (o for o in src() if o.__getattribute__(field) > value)
                case ">=":
                    return (o for o in src() if o.__getattribute__(field) >= value)
                case _:
                    raise ValueError(f"Unknown operator {op}")

        return BaseQuery(it)

    def get_all(self) -> Iterator[T]:
        """Get all the items after applying filters"""
        return self._src()
