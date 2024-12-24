"""Base class for storage implementations which store Pydantic objects"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterator, Type

from pydantic import BaseModel


class KeyException(Exception):
    def __init__(
        self, collection_name: str = None, clazz: Type = None, key: str = None
    ):
        self.collection_name = collection_name
        self.clazz = clazz
        self.key = key


class KeyNotExistsException(KeyException):
    def __init__(
        self, collection_name: str = None, clazz: Type = None, key: str = None
    ):
        super().__init__(collection_name, clazz, key)


class KeyExistsException(KeyException):
    def __init__(
        self, collection_name: str = None, clazz: Type = None, key: str = None
    ):
        super().__init__(collection_name, clazz, key)


class BaseStorage[T: BaseModel](ABC):
    """Base class for storage implementations which store Pydantic objects"""

    def __init__(self, collection_name: str, clazz: Type[T], key_name: str = None):
        self.collection_name = collection_name
        self.clazz = clazz
        if not key_name:
            field_names = list(clazz.model_fields.keys())
            key_name = field_names[0]
        self.key_name = key_name

    @abstractmethod
    def put(self, key: str, value: T) -> None:
        """Store the value with the key"""

    @abstractmethod
    def get(self, key: str) -> T:
        """Get the value with the key"""

    @abstractmethod
    def keys(self) -> Iterator[T]:
        """Get all the keys"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the value with the key"""

    def create(self, value: T) -> None:
        """Adds to collection a new element but only if such key doesn't already exists"""
        key = self.get_key(value)
        if self.key_exists(key):
            raise KeyExistsException
        self.put(key, value)

    def save(self, value: T) -> None:
        key = self.get_key(value)
        self.put(key, value)

    def get_key(self, value: T) -> str:
        return getattr(value, self.key_name)

    def drop(self) -> None:
        """Delete all the values"""
        for key in self.keys():
            self.delete(key)

    def get_all(self, sort: Any = None) -> Iterator[T]:
        """Get all the values"""
        for key in self.keys():
            yield self.get(key)

    def key_exists(self, needle: str) -> bool:
        for key in self.keys():
            if needle == key:
                return True
        return False

    def is_empty(self) -> bool:
        """Is storage empty?"""
        for _ in self.keys():
            return False
        return True
