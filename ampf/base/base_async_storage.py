"""Base class for storage implementations which store Pydantic objects"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable, Optional, Type

from pydantic import BaseModel

from .exceptions import KeyExistsException


class BaseAsyncStorage[T: BaseModel](ABC):
    """Base class for storage implementations which store Pydantic objects"""

    def __init__(
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[str | Callable[[T], str]] = None,
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        if not key and not key_name:
            field_names = list(clazz.model_fields.keys())
            key = field_names[0]
        self.key = key or key_name

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
