from __future__ import annotations

import logging
from abc import ABC
from typing import Any, AsyncIterable, AsyncIterator, Callable, List, Optional, Tuple

from pydantic import BaseModel

from .base_query import OP


class BaseAsyncQuery[T: BaseModel](ABC):
    """Base query with a defalt, brute force implementation."""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        src: Callable[[], AsyncIterator[T]],
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        self._src = src
        self.embedding_field_name = embedding_field_name
        self.embedding_search_limit = embedding_search_limit

    def where(self, field: str, op: OP, value: Any) -> BaseAsyncQuery[T]:
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
                    case "in":
                        if attr in value:
                            yield o

        return BaseAsyncQuery(it)

    async def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> AsyncIterable[T]:
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
            async for item in self.get_all():
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

    async def get_all(self) -> AsyncIterator[T]:
        """Get all the items after applying filters"""
        # Asynchronously iterate over the source and yield each item.
        # This makes get_all an async generator itself.
        async for item in self._src():
            yield item
