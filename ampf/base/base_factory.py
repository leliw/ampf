from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel


from .base_storage import BaseStorage
from .base_blob_storage import BaseBlobStorage


class BaseFactory(ABC):
    """Factory creating storage objects"""

    @abstractmethod
    def create_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T], key_name: str = None
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
        self, collection_name: str, clazz: Type[T], key_name: str = None
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
        return self.create_storage(collection_name, clazz, key_name)

    @abstractmethod
    def create_blob_storage[T: BaseModel](
        self, collection_name: str, clazz: Type[T] = None, content_type: str = None
    ) -> BaseBlobStorage[T]:
        """Creates blob storage for items of given class.

        Args:
            collection_name: name of the collection where blobs are stored
            clazz: class of metadata
            content_type: content type of blobs
        Returns:
            Blob storage object.
        """
