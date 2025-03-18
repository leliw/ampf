from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Type

from pydantic import BaseModel


class FileNameMimeType(BaseModel):
    name: str
    mime_type: str


class BaseBlobStorage[T: BaseModel](ABC):
    """Base class for blob storage implementations"""

    def __init__(self, collection_name: str, clazz: Type[T], content_type: str = None):
        """Initializes the storage

        Args:
            bucket_name: The name of the bucket
            clazz: The class of the metadata
            content_type: The content type of the blob
        """
        self.collection_name = collection_name
        self.clazz = clazz
        self.content_type = content_type

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
    def list_blobs(self, dir: str = None) -> Iterator[FileNameMimeType]:
        """Lists all the blobs in the storage

        Args:
            dir: The directory to list
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

    @abstractmethod
    def delete_folder(self, folder_name: str):
        """Deletes a folder from the storage

        Args:
            folder_name: The name of the folder
        """

    def move_blob(self, source_key: str, dest_key: str):
        """Moves a blob to another location in the storage

        Args:
            source_key: The key of the source blob
            dest_key: The key of the destination blob
        """
        data = self.download_blob(source_key)
        metadata = self.get_metadata(source_key)
        self.delete(source_key)
        self.upload_blob(dest_key, data, metadata)

    def upload_file(
        self,
        file_path: Path,
        metadata: T = None,
        key: str = None,
        content_type: str = None,
    ) -> None:
        """Uploads a file to the storage

        Args:
            file_path: The path to the file
            metadata: The metadata of the file
            key: The key of the file
            content_type: The content type of the file
        """
        with open(file_path, "rb") as file:
            file_content = file.read()
        if not key:
            key = file_path.stem
        self.upload_blob(key, file_content, metadata, content_type)
