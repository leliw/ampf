"""Base class for storage implementations which store Pydantic objects"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable, Iterator, List, Optional, Tuple, Type

from pydantic import BaseModel

from .exceptions import KeyExistsException


class BaseStorage[T: BaseModel](ABC):
    """Base class for storage implementations which store Pydantic objects"""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[str | Callable[[T], str]] = None,
        embedding_field_name: str = "embedding",
        embedding_search_limit: int = 5,
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        if not key and not key_name:
            key = BaseStorage._find_key_name(clazz)
        self.key = key or key_name
        self.embedding_field_name = embedding_field_name
        self.embedding_search_limit = embedding_search_limit

    @classmethod
    def _find_key_name(cls, clazz: Type[T]) -> str:
        field_names = list(clazz.model_fields.keys())
        if "id" in field_names:
            return "id"
        elif "uuid" in field_names:
            return "uuid"
        elif "uid" in field_names:
            return "uid"
        else:
            return field_names[0]
    

    @abstractmethod
    def put(self, key: Any, value: T) -> None:
        """Store the value with the key"""

    @abstractmethod
    def get(self, key: Any) -> T:
        """Get the value with the key"""

    @abstractmethod
    def keys(self) -> Iterable[str]:
        """Get all the keys"""

    @abstractmethod
    def delete(self, key: Any) -> None:
        """Delete the value with the key"""

    def create(self, value: T) -> None:
        """Adds to collection a new element but only if such key doesn't already exists"""
        key = self.get_key(value)
        if self.key_exists(key):
            raise KeyExistsException
        self.put(key, value)

    def save(self, value: T) -> None:
        """Save the value in the storage. The key is calculated based on the value.
        If the key already exists, it will be overwritten.
        """
        key = self.get_key(value)
        self.put(key, value)

    def get_key(self, value: T) -> str:
        """Get the key for the value"""
        if self.key and isinstance(self.key, Callable):
            return str(self.key(value))
        elif self.key and isinstance(self.key, str):
            return str(getattr(value, self.key))
        else:
            raise ValueError("Key name or key function must be provided")

    def drop(self) -> None:
        """Delete all the values"""
        for key in self.keys():
            self.delete(key)

    def get_all(self, sort: Any = None) -> Iterator[T]:
        """Get all the values"""
        for key in self.keys():
            yield self.get(key)

    def key_exists(self, needle: Any) -> bool:
        """Check if the key exists"""
        needle = str(needle)
        for key in self.keys():
            if needle == key:
                return True
        return False

    def is_empty(self) -> bool:
        """Is storage empty?"""
        for _ in self.keys():
            return False
        return True

    def count(self) -> int:
        return len(list(self.keys()))

    def create_collection(
        self,
        parent_key: str,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
    ) -> BaseStorage[T]:
        new_collection_name = f"{self.collection_name}/{parent_key}/{collection_name}"
        return self.__class__(new_collection_name, clazz, key=key)

    def find_nearest(self, embedding: List[float], limit: Optional[int] = None) -> Iterator[T]:
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
