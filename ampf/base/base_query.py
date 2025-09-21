from __future__ import annotations

import logging
from abc import ABC
from typing import Any, Callable, Iterator, List, Optional, Tuple, Type

from pydantic import BaseModel
from typing_extensions import Literal

OP = Literal["==", "!=", "<", "<=", ">", ">=", "in"]

class BaseQuery[T: BaseModel](ABC):
    """Base query with defalt, brute force implementation."""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        src: Callable[[], Iterator[T]],
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        self._src = src
        self.embedding_field_name = embedding_field_name
        self.embedding_search_limit = embedding_search_limit

    def where(self, field: str, op: OP, value: Any) -> BaseQuery[T]:
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
                case "in":
                    return (o for o in src() if o.__getattribute__(field) in value)
                case _:
                    raise ValueError(f"Unknown operator {op}")

        return BaseQuery(it)

    def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> Iterator[T]:
        """Finds the nearest knowledge base items to the given vector.

        Args:
            embedding: The vector to search for.
            limit: The maximum number of results to return.
        Returns:
            An iterator of the nearest items.
        """
        try:
            from sentence_transformers.util import cos_sim

            self._log.warning("Embedding search is not optimized for performance.")
            self._log.warning("Consider using a vector database for production.")

            limit = limit or self.embedding_search_limit
            ret: List[Tuple[T, float]] = []
            for item in self.get_all():
                em = getattr(item, self.embedding_field_name)
                if em:
                    similarity = cos_sim(embedding, em)
                    ret.append((item, similarity.item()))
            ret.sort(key=lambda x: x[1], reverse=True)
            for item in ret[:limit]:
                yield item[0]
        except ImportError:
            self._log.error("The package `sentence_transformers` is not installed ")
            self._log.error("Try: pip install ampf[huggingface]")

    def get_all(self) -> Iterator[T]:
        """Get all the items after applying filters"""
        return self._src()
