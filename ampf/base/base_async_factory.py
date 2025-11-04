import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional, Type

from pydantic import BaseModel

from .base_async_blob_storage import BaseAsyncBlobStorage
from .base_async_collection_storage import BaseAsyncCollectionStorage
from .base_async_query_storage import BaseAsyncQueryStorage
from .blob_model import Blob, BlobLocation
from .collection_def import CollectionDef
from .exceptions import KeyNotExistsException

_log = logging.getLogger(__name__)


class BaseAsyncFactory(ABC):
    """Factory creating async storage objects"""

    @abstractmethod
    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: Type[T],
        key: Optional[str | Callable[[T], str]] = None,
    ) -> BaseAsyncQueryStorage[T]:
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
        key: Optional[str | Callable[[T], str]] = None,
    ) -> BaseAsyncQueryStorage[T]:
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
        return self.create_storage(collection_name, clazz, key)

    @abstractmethod
    def create_blob_storage[T: BaseModel](
        self,
        collection_name: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> BaseAsyncBlobStorage[T]:
        """Creates blob storage for items of given class.

        Args:
            collection_name: name of the collection where blobs are stored
            clazz: class of metadata
            content_type: content type of blobs
            bucket_name: name of the bucket where blobs are stored
        Returns:
            Blob storage object.
        """

    def create_collection[T: BaseModel](self, definition: CollectionDef[T] | dict) -> BaseAsyncCollectionStorage[T]:
        """Creates collection from its definition. Definition can contain also subcollections definitions.

        Args:
            definition: Collection definition
        Returns:
            Collection object.
        """
        if isinstance(definition, dict):
            definition = CollectionDef.model_validate(dict)
        return BaseAsyncCollectionStorage(self.create_storage, definition)

    def create_storage_tree[T: BaseModel](self, root: CollectionDef[T]) -> BaseAsyncCollectionStorage[T]:
        """Creates storage tree from its definition.

        Args:
            root: Collection definition
        Returns:
            Collection object.
        """
        return self.create_collection(root)

    async def download_blob(self, blob_location: BlobLocation) -> Blob:
        """Downloads a blob from the specified file location.

        Args:
            file_location (FileLocation): The location of the file to load.

        Returns:
            Blob: The loaded blob.
        """
        try:
            bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
            return await bs.download_async(blob_location.name)
        except KeyNotExistsException as e:
            _log.warning("Error translating file: %s", blob_location.name)
            raise e

    async def upload_blob(self, blob_location: BlobLocation, blob: Blob) -> None:
        """Uploads a blob to the specified file location.

        Args:
            file_location (FileLocation): The location to save the blob.
            blob (Blob): The blob to save.
        """
        bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
        await bs.upload_async(blob)
