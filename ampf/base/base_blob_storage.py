from abc import ABC, abstractmethod
from typing import Iterator, Type

from pydantic import BaseModel


class BaseBlobStorage[T: BaseModel](ABC):
    """Base class for blob storage implementations"""

    def __init__(self, bucket_name: str, clazz: Type[T], content_type: str = None):
        """Initializes the storage

        Args:
            bucket_name: The name of the bucket
            clazz: The class of the metadata
            content_type: The content type of the blob
        """
        self.bucket_name = bucket_name
        self.clazz = clazz
        self.contet_type = content_type

    @abstractmethod
    def upload_blob(
        self, key: str, data: bytes, metadata: T = None, content_type: str = None
    ) -> None:
        """Uploads a blob to the storage

        Args:
            key: The key of the blob
            data: The data of the blob
            metadata: The metadata of the blob
            content_type: The content type of the blob
        """

    @abstractmethod
    def download_blob(self, key: str) -> bytes:
        """Downloads a blob from the storage

        Args:
            key: The key of the blob
        """

    @abstractmethod
    def put_metadata(self, key: str, metadata: T) -> None:
        """Puts metadata for a blob

        Args:
            key: The key of the blob
            metadata: The metadata of the blob
        """

    @abstractmethod
    def get_metadata(self, key: str) -> T:
        """Gets metadata for a blob

        Args:
            key: The key of the blob
        """

    @abstractmethod
    def delete(self, key: str):
        """Deletes a blob from the storage

        Args:
            key: The key of the blob
        """

    @abstractmethod
    def keys(self) -> Iterator[str]:
        """Gets the keys of all blobs in the storage"""

    def drop(self) -> None:
        """Deletes all the blobs from the storage"""
        for key in self.keys():
            self.delete(key)
