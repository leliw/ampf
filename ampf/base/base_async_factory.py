import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

from .base_async_blob_storage import BaseAsyncBlobStorage
from .base_async_collection_storage import BaseAsyncCollectionStorage
from .base_async_query_storage import BaseAsyncQueryStorage
from .base_topic import BaseTopic
from .blob_model import BaseBlobMetadata, Blob, BlobLocation
from .collection_def import CollectionDef
from .exceptions import KeyNotExistsException

_log = logging.getLogger(__name__)


class BaseAsyncFactory(ABC):
    """Factory creating async storage objects"""

    def __init__(self):
        self._collection_defs: dict[str, CollectionDef] = {}
        self._type_to_collection_defs: dict[Type[BaseModel], CollectionDef] = {}

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
            key: name of item's property which is used as a key or a function to extract key

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
            definition = CollectionDef.model_validate(definition)
        return BaseAsyncCollectionStorage(self.create_storage, definition)

    def create_storage_tree[T: BaseModel](self, root: CollectionDef[T]) -> BaseAsyncCollectionStorage[T]:
        """Creates storage tree from its definition.

        Args:
            root: Collection definition
        Returns:
            Collection object.
        """
        return self.create_collection(root)

    def register_collections(self, definitions: list[CollectionDef[Any]]):
        """Registers a list of collection definitions.

        Args:
            definitions: List of collection definitions.
        """
        for definition in definitions:
            self._collection_defs[definition.collection_name] = definition
            if definition.clazz:
                self._type_to_collection_defs[definition.clazz] = definition

    def get_collection[T: BaseModel](self, collection_name_or_type: str | Type[T]) -> BaseAsyncCollectionStorage[T]:
        """Retrieves a collection by its name or type from the registered definitions.

        Args:
            collection_name_or_type: The name or type of the collection.
        Returns:
            The collection object.
        """
        if isinstance(collection_name_or_type, type):
            if collection_name_or_type not in self._type_to_collection_defs:
                raise KeyNotExistsException(f"Collection for type {collection_name_or_type.__name__} not registered")
            definition = self._type_to_collection_defs[collection_name_or_type]
        else:
            if collection_name_or_type not in self._collection_defs:
                raise KeyNotExistsException(f"Collection {collection_name_or_type} not registered")
            definition = self._collection_defs[collection_name_or_type]
        return self.create_collection(definition)

    async def download_blob(self, blob_location: BlobLocation) -> Blob:
        """Downloads a blob from the specified file location.

        Args:
            blob_location (BlobLocation): The location of the file to load.

        Returns:
            Blob: The loaded blob.
        """
        try:
            bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
            return await bs.download_async(blob_location.name)
        except KeyNotExistsException as e:
            _log.warning("Error downloading blob: %s", blob_location.name)
            raise e

    async def upload_blob(self, blob_location: BlobLocation, blob: Blob) -> None:
        """Uploads a blob to the specified file location.

        Args:
            blob_location (BlobLocation): The location to save the blob.
            blob (Blob): The blob to save.
        """
        bs = self.create_blob_storage("", bucket_name=blob_location.bucket)
        await bs.upload_async(blob)

    def create_topic(self, topic_id: str) -> BaseTopic[BaseModel]:
        """Creates a topic (object sender to publish messages to it).

        Args:
            topic_id: The ID of the topic.
        Returns:
            The created BaseTopic object.
        """
        raise NotImplementedError(f"create_topic() method is not implemented in {self.__class__.__name__}")

    async def publish_message(
        self,
        topic_id: str,
        data: BaseModel | str | bytes,
        response_topic: Optional[str] = None,
        sender_id: Optional[str] = None,
    ) -> str:
        """Publishes a message to the specified topic.

        Args:
            topic_id: The ID of the topic.
            data: The message to publish.
            response_topic: The ID of the response topic.
            sender_id: The ID of the sender.
        Returns:
            The message ID.
        """
        topic = self.create_topic(topic_id)
        return await topic.publish_async(data, response_topic=response_topic, sender_id=sender_id)

    def create_blob_location(self, name: str, bucket: Optional[str] = None) -> BlobLocation:
        """Creates a BlobLocation object.

        Args:
            name: The name of the blob.
            bucket: The name of the bucket.
        Returns:
            The created BlobLocation object.
        """
        return BlobLocation(name=name, bucket=bucket)
