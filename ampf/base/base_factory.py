import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from ampf.base.base_topic import BaseTopic
from ampf.base.collection_def import CollectionDef
from ampf.base.exceptions import KeyNotExistsException

from .base_blob_storage import BaseBlobStorage
from .base_collection_storage import BaseCollectionStorage
from .base_query_storage import BaseQueryStorage
from .blob_model import BaseBlobMetadata, Blob, BlobLocation

_log = logging.getLogger(__name__)


class BaseFactory(ABC):
    """Factory creating objects"""

    def __init__(self, collection_defs: list[CollectionDef[Any]] | None = None):
        self._collection_defs: dict[str, CollectionDef] = {}
        self._type_to_collection_defs: dict[type[BaseModel], CollectionDef] = {}
        if collection_defs:
            self.register_collections(collection_defs)

    @abstractmethod
    def create_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ) -> BaseQueryStorage[T]:
        """Creates standard key-value storage for items of given class.

        Args:
            collection_name: name of collection where items are stored
            clazz: class of items
            key: name of item's property which is used as a key or a function to extract key

        Returns:
            Storage object.
        """

    def create_compact_storage[T: BaseModel](
        self,
        collection_name: str,
        clazz: type[T],
        key: str | Callable[[T], str] | None = None,
    ) -> BaseQueryStorage[T]:
        """Creates _compact_ key-value storage for items of given class.

        It should be used for smaller collections.
        It creates standard storage by default.

        Args:
            collection_name: name of collection where items are stored
            clazz: class of items
            key: name of item's property which is used as a key or a function to extract key

        Returns:
            Storage object.
        """
        return self.create_storage(collection_name, clazz, key)

    @abstractmethod
    def create_blob_storage[T: BaseBlobMetadata](
        self,
        collection_name: str | None = None,
        clazz: type[T] | None = None,
        content_type: str | None = None,
        bucket_name: str | None = None,
    ) -> BaseBlobStorage[T]:
        """Creates blob storage for items of given class.

        Args:
            collection_name: name of the collection where blobs are stored
            clazz: class of metadata
            content_type: content type of blobs
            bucket_name: name of the bucket where blobs are stored
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
            definition = CollectionDef(**definition)
        return BaseCollectionStorage(self.create_storage, definition) # pyright: ignore[reportAbstractUsage]

    def create_storage_tree[T: BaseModel](self, root: CollectionDef[T]) -> BaseCollectionStorage[T]:
        """Creates storage tree from its definition.

        Args:
            root: Collection definition
        Returns:
            Collection object.
        """
        return self.create_collection(root)

    def register_collections(self, definitions: list[CollectionDef[Any]]) -> None:
        """Registers a list of collection definitions.

        Args:
            definitions: List of collection definitions.
        """
        for definition in definitions:
            self._collection_defs[definition.collection_name] = definition
            if definition.clazz:
                self._type_to_collection_defs[definition.clazz] = definition
        try:
            from ampf.dependency.dependency_registry import DependencyRegistry

            def register_storage(sd):
                @DependencyRegistry.register_for_type(BaseCollectionStorage[sd.clazz])  # type: ignore
                def get_collection():
                    return self.get_collection(sd.clazz)

            for sd in definitions:
                register_storage(sd)
        except ImportError:
            pass

    def get_collection[T: BaseModel](self, collection_name_or_type: str | type[T] | Any) -> BaseCollectionStorage[T]:
        """Retrieves a collection by its name or type from the registered definitions.

        Args:
            collection_name_or_type: The name or type of the collection.
        Returns:
            The collection object.
        """
        if isinstance(collection_name_or_type, str):
            if collection_name_or_type not in self._collection_defs:
                raise KeyNotExistsException(f"Collection {collection_name_or_type} not registered")
            definition = self._collection_defs[collection_name_or_type]
        else:
            if collection_name_or_type not in self._type_to_collection_defs:
                raise KeyNotExistsException(f"Collection for type {collection_name_or_type.__name__} not registered")
            definition = self._type_to_collection_defs[collection_name_or_type]
        return self.create_collection(definition)

    def create_blob_location(self, name: str, bucket: str | None = None) -> BlobLocation:
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
            blob_location: The location of the file to load.

        Returns:
            Blob: The loaded blob.
        """
        try:
            bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
            return bs.download(blob_location.name)
        except KeyNotExistsException:
            _log.warning("Error downloading blob: %s", blob_location.name)
            raise

    def upload_blob(self, blob_location: BlobLocation, blob: Blob) -> None:
        """Uploads a blob to the specified file location.

        Args:
            blob_location: The location to save the blob.
            blob: The blob to save.
        """
        bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
        bs.upload(blob)

    def delete_blob(self, blob_location: BlobLocation) -> None:
        """Deletes a blob from the specified file location.

        Args:
            blob_location: The location of the file to delete.
        """
        bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
        bs.delete(blob_location.name)

    def create_topic(self, topic_id: str) -> BaseTopic[BaseModel]:
        """Creates a topic (a sender object to publish messages to)

        Args:
            topic_id: The ID of the topic.
        Returns:
            The created BaseTopic object.
        """
        raise NotImplementedError(f"create_topic() method is not implemented in {self.__class__.__name__}")
