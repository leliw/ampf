from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Type

from pydantic import BaseModel, Field

from .base_blob_storage import BaseBlobStorage
from .base_collection_storage import BaseCollectionStorage
from .base_storage import BaseStorage


class CollectionDef(BaseModel):
    """Parameters defining CollectionStorage"""

    collection_name: str
    clazz: Type
    key_name: Optional[str] = None
    subcollections: Optional[List[CollectionDef]] = Field(default_factory=list)

    def __init__(
        self,
        collection_name: str,
        clazz: Type,
        key_name: Optional[str] = None,
        subcollections: Optional[List[CollectionDef]] = None,
    ):
        super().__init__(
            collection_name=collection_name,
            clazz=clazz,
            key_name=key_name,
            subcollections=subcollections or list(),
        )


class BaseFactory(ABC):
    """Factory creating storage objects"""

    @abstractmethod
    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseStorage[T]:
        """Creates standard key-value storage for items of given class.

        Args:
            collection_name: name of collection where items are stored
            clazz: class of items
            key_name: name of item's property which is used as a key

        Returns:
            Storage object.
        """

    def create_compact_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key_name: Optional[str] = None,
        key: Optional[Callable[[T], str]] = None,
    ) -> BaseStorage[T]:
        """Creates _compact_ key-value storage for items of given class.

        It should be used fro smaller collections.
        It creates standard storage by default.

                Args:
            collection_name: name of collection where items are stored
            clazz: class of items
            key_name: name of item's property which is used as a key

        Returns:
            Storage object.
        """
        return self.create_storage(collection_name, clazz, key_name, key)

    @abstractmethod
    def create_blob_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
    ) -> BaseBlobStorage[T]:
        """Creates blob storage for items of given class.

        Args:
            collection_name: name of the collection where blobs are stored
            clazz: class of metadata
            content_type: content type of blobs
        Returns:
            Blob storage object.
        """

    def create_collection[T: BaseModel](
        self, definition: CollectionDef[T] | dict
    ) -> BaseCollectionStorage[T]:
        """Creates collection from its definition. Definition can contain also subcollections definitions.

        Args:
            definition: Collection definition
        Returns:
            Collection object.
        """
        if isinstance(definition, dict):
            definition = CollectionDef.model_validate(dict)
        ret: BaseCollectionStorage = self.create_storage(
            definition.collection_name, definition.clazz, definition.key_name
        )
        for subcol in definition.subcollections:
            ret.add_collection(self.create_collection(subcol))
        return ret
