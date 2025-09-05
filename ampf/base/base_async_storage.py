"""Base class for storage implementations which store Pydantic objects"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterable, AsyncIterator, Callable, List, Optional, Tuple, Type

from pydantic import BaseModel

from ampf.base.base_storage import BaseStorage

from .exceptions import KeyExistsException


class BaseAsyncStorage[T: BaseModel](ABC):
    """Base class for storage implementations which store Pydantic objects"""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        if not key:
            key = BaseStorage._find_key_name(clazz)
        self.key = key
        self.embedding_field_name = embedding_field_name
        self.embedding_search_limit = embedding_search_limit


    @abstractmethod
    async def put(self, key: Any, value: T) -> None:
        """Store the value with the key"""

    @abstractmethod
    async def get(self, key: Any) -> T:
        """Get the value with the key"""

    @abstractmethod
    async def keys(self) -> AsyncIterator[str]:
        """Get all the keys"""
        yield "None"

    @abstractmethod
    async def delete(self, key: Any) -> None:
        """Delete the value with the key"""

    async def create(self, value: T) -> None:
        """Adds to collection a new element but only if such key doesn't already exists"""
        key = self.get_key(value)
        if await self.key_exists(key):
            raise KeyExistsException
        await self.put(key, value)

    async def save(self, value: T) -> None:
        key = self.get_key(value)
        await self.put(key, value)

    def get_key(self, value: T) -> str:
        """Get the key for the value"""
        if self.key and isinstance(self.key, Callable):
            return str(self.key(value))
        elif self.key and isinstance(self.key, str):
            return str(getattr(value, self.key))
        else:
            raise ValueError("Key name or key function must be provided")

    async def drop(self) -> None:
        """Delete all the values"""
        async for key in self.keys():
            await self.delete(key)

    async def get_all(self, sort: Any = None) -> AsyncIterator[T]:
        """Get all the values"""
        async for key in self.keys():
            yield await self.get(key)

    async def key_exists(self, needle: Any) -> bool:
        needle = str(needle)
        async for key in self.keys():
            if needle == key:
                return True
        return False

    async def is_empty(self) -> bool:
        """Is storage empty?"""
        async for _ in self.keys():
            return False
        return True

    async def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> AsyncIterable[T]:
        """Finds the nearest knowledge base items to the given vector.

        Args:
            embedding: The vector to search for.
            limit: The maximum number of results to return.
        Returns:
            An iterator of the nearest items.
        """
        try:
            self._log
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
