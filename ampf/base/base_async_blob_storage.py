from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Type

from pydantic import BaseModel

from .blob_model import Blob, BlobHeader


class BaseAsyncBlobStorage[T: BaseModel](ABC):
    """
    Abstract base class for asynchronous blob storage operations.
    This class defines the interface for uploading, downloading, deleting,
    checking existence, and listing blobs.
    """

    def __init__(
        self, collection_name: Optional[str] = None, clazz: Optional[Type[T]] = None, content_type: str = "text/plain"
    ):
        """
        Initializes the storage.

        Args:
            collection_name: The name of the collection (root folder)
            clazz: The class of the metadata.
            content_type: The content type of the blobs.
        """
        self.collection_name = collection_name
        self.clazz = clazz
        self.content_type = content_type

    @abstractmethod
    async def upload_async(self, blob: Blob[T]) -> None:
        """
        Uploads binary data to the storage.

        Args:
            blob: The blob object containing data and metadata to upload.
        """
        pass

    @abstractmethod
    async def download_async(self, name: str) -> Blob[T]:
        """
        Downloads binary data based on the blob key.

        Args:
            name: The name identifying the blob to download.

        Returns:
            The downloaded blob object.
        """
        pass

    @abstractmethod
    def delete(self, name: str) -> None:
        """
        Deletes a blob with the given name.

        Args:
            name: The name of the blob to delete.
        """
        pass

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Checks if a blob with the given name exists."""
        pass

    @abstractmethod
    def list_blobs(self, prefix: Optional[str] = None) -> List[BlobHeader[T]]:
        """Returns a list of blob headers, optionally filtered by a prefix."""
        pass

    def put_metadata(self, name: str, metadata: T) -> None:
        pass

    def get_metadata(self, name: str) -> Optional[T]:
        pass

    def names(self, prefix: Optional[str] = None) -> Iterable[str]:
        return [blob.name for blob in self.list_blobs(prefix)]

    def drop(self) -> None:
        for name in self.names():
            self.delete(name)

    def delete_folder(self, folder_name: str) -> None:
        for name in self.names(folder_name):
            self.delete(name)