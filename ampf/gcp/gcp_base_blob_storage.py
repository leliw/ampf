import logging
from typing import Iterable, Optional, Type

from google.cloud import storage
from pydantic import BaseModel

from ampf.base.blob_model import BlobHeader
from ampf.base.exceptions import KeyNotExistsException


class GcpBaseBlobStorage[T: BaseModel]:
    """A simple wrapper around Google Cloud Storage.
    It contains common methods for sync and async blob storage.
    """

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        bucket_name: str,
        collection_name: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        content_type: str = "text/plain",
        storage_client: Optional[storage.Client] = None,
    ):
        self.bucket_name = bucket_name
        collection_name = (
            collection_name[1:] if collection_name and collection_name.startswith("/") else collection_name
        )
        collection_name = collection_name[:-1] if collection_name and collection_name.endswith("/") else collection_name
        self.collection_name = collection_name
        self.clazz = clazz
        self.content_type = content_type
        self._storage_client = storage_client or storage.Client()
        if bucket_name:
            self._bucket = self._storage_client.bucket(bucket_name)
        else:
            raise ValueError(
                f"No bucket specified or found for collection '{collection_name}'. Please provide a valid bucket_name."
            )

    def get_full_name(self, name: str) -> str:
        """Returns the full name of the blob (with collection name if any)

        Args:
            name: The name of the blob.

        Returns:
            The full name of the blob.
        """
        name = name[1:] if name and name.startswith("/") else name
        return f"{self.collection_name}/{name}" if self.collection_name else name

    def _get_blob(self, name: str) -> storage.Blob:
        return self._bucket.blob(self.get_full_name(name))

    def list_blobs(self, prefix: Optional[str] = None) -> Iterable[BlobHeader[T]]:
        """Returns a list of blob headers, optionally filtered by a prefix.
        
        Args:
            prefix: The prefix to filter the blobs by.
        
        Returns:
            A list of blob headers.
        """
        prefix = self.get_full_name(prefix or "")
        col_name_len = len(self.collection_name) + 1 if self.collection_name else 0
        for blob in self._bucket.list_blobs(prefix=prefix):
            yield BlobHeader(
                name=blob.name[col_name_len:],
                content_type=blob.content_type,
                metadata=self.clazz(**blob.metadata) if self.clazz and blob.metadata else None,
            )

    def delete(self, name: str) -> None:
        """Deletes a blob with the given name.

        Args:
            name: The name of the blob to delete.
        """
        blob = self._get_blob(name)
        blob.delete()

    def exists(self, name: str) -> bool:
        """Checks if a blob with the given name exists.

        Args:
            name: The name of the blob to check.

        Returns:
            True if the blob exists, False otherwise.
        """
        blob = self._get_blob(name)
        return blob.exists()

    def put_metadata(self, name: str, metadata: T) -> None:
        """Puts metadata for a blob.

        Args:
            name: The name of the blob.
            metadata: The metadata to put.
        """
        blob = self._get_blob(name)
        blob.metadata = metadata.model_dump()
        blob.patch()

    def get_metadata(self, name: str) -> Optional[T]:
        """Gets metadata for a blob.

        Args:
            name: The name of the blob.

        Returns:
            The metadata of the blob.
        """
        blob = self._get_blob(name)
        if not blob.exists():
            raise KeyNotExistsException(self.collection_name, self.clazz, name)
        if not blob.metadata:
            # I don't know why, but sometimes the metadata is None (ML)
            blob.reload()
        if not blob.metadata or not self.clazz:
            return None
        return self.clazz(**blob.metadata)
