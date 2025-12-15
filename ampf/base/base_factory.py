from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional, Type

from pydantic import BaseModel

from ampf.base.exceptions import KeyNotExistsException

from .base_blob_storage import BaseBlobStorage
from .base_collection_storage import BaseCollectionStorage, CollectionDef
from .base_query_storage import BaseQueryStorage
from .blob_model import Blob, BlobLocation

_log = logging.getLogger(__name__)


class BaseFactory(ABC):
    """Factory creating storage objects"""

    @abstractmethod
    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        key_name: Optional[str] = None,
    ) -> BaseQueryStorage[T]:
        """Creates standard key-value storage for items of given class.

        Args:
            collection_name: name of collection where items are stored
            clazz: class of items
            key: name of item's property which is used as a key

        Returns:
            Storage object.
        """

    def create_compact_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
        key_name: Optional[str] = None,
    ) -> BaseQueryStorage[T]:
        """Creates _compact_ key-value storage for items of given class.

        It should be used fro smaller collections.
        It creates standard storage by default.

        Args:
            collection_name: name of collection where items are stored
            clazz: class of items
            key: name of item's property which is used as a key

        Returns:
            Storage object.
        """
        return self.create_storage(collection_name, clazz, key or key_name)

    @abstractmethod
    def create_blob_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> BaseBlobStorage[T]:
        """Creates blob storage for items of given class.

        Args:
            collection_name: name of the collection where blobs are stored
            clazz: class of metadata
            content_type: content type of blobs
        Returns:
            Blob storage object.
        """

    def create_collection[T: BaseModel](self, definition: CollectionDef[T] | dict) -> BaseCollectionStorage[T]:
        """Creates collection from its definition. Definition can contain also subcollections definitions.

        Args:
            definition: Collection definition
        Returns:
            Collection object.
        """
        if isinstance(definition, dict):
            definition = CollectionDef.model_validate(dict)
        return BaseCollectionStorage(self.create_storage, definition)

    def create_storage_tree[T: BaseModel](self, root: CollectionDef[T]) -> BaseCollectionStorage[T]:
        """Creates storage tree from its definition.

        Args:
            root: Collection definition
        Returns:
            Collection object.
        """
        return self.create_collection(root)

    def create_blob_location(
        self, name: str, bucket: Optional[str] = None
    ) -> BlobLocation:
        """Creates a BlobLocation object.

        Args:
            name: The name of the blob.
            bucket: The name of the bucket.
        Returns:
            The created BlobLocation object.
        """
        return BlobLocation(name=name, bucket=bucket)

    def download_blob(self, blob_location: BlobLocation) -> Blob:
        """Downloads a blob from the specified file location.

        Args:
            file_location (FileLocation): The location of the file to load.

        Returns:
            Blob: The loaded blob.
        """
        try:
            bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
            return bs.download(blob_location.name)
        except KeyNotExistsException as e:
            _log.warning("Error translating file: %s", blob_location.name)
            raise e

    def upload_blob(self, blob_location: BlobLocation, blob: Blob) -> None:
        """Uploads a blob to the specified file location.

        Args:
            file_location (FileLocation): The location to save the blob.
            blob (Blob): The blob to save.
        """
        bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
        bs.upload(blob)

