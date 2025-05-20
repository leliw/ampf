from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from .blob_model import Blob, BlobHeader


class BaseBlobAsyncStorage[T: BaseModel](ABC):
    """
    Abstract base class for asynchronous blob storage operations.
    This class defines the interface for uploading, downloading, deleting,
    checking existence, and listing blobs.
    """

    @abstractmethod
    async def upload_async(self, blob: Blob[T]) -> None:
        """
        Uploads binary data to the storage.

        Args:
            blob: The blob object containing data and metadata to upload.
        """
        pass

    @abstractmethod
    async def download_async(self, key: str) -> Blob[T]:
        """
        Downloads binary data based on the blob key.

        Args:
            key: The key identifying the blob to download.

        Returns:
            The downloaded blob object.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Deletes a blob with the given key.

        Args:
            key: The key of the blob to delete.
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Checks if a blob with the given key exists."""
        pass

    @abstractmethod
    def list_blobs(self, prefix: Optional[str] = None) -> list[BlobHeader]:
        """Returns a list of blob headers, optionally filtered by a prefix."""
        pass
