from abc import ABC, abstractmethod
from typing import AsyncGenerator, Awaitable, Callable, Optional, Type

from .blob_model import BaseBlobMetadata, Blob, BlobHeader


class BaseAsyncBlobStorage[T: BaseBlobMetadata](ABC):
    """
    Abstract base class for asynchronous blob storage operations.
    This class defines the interface for uploading, downloading, deleting,
    checking existence, and listing blobs.
    """

    def __init__(
        self, collection_name: Optional[str] = None, clazz: Type[T] = BaseBlobMetadata, content_type: Optional[str] = None
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
    def list_blobs(self, prefix: Optional[str] = None) -> AsyncGenerator[BlobHeader[T]]:
        """Returns a list of blob headers, optionally filtered by a prefix."""
        pass

    @abstractmethod
    async def put_metadata(self, name: str, metadata: T) -> None:
        pass
    
    @abstractmethod
    async def get_metadata(self, name: str) -> Optional[T]:
        pass

    async def names(self, prefix: Optional[str] = None) -> AsyncGenerator[str]:
        async for blob_header in self.list_blobs(prefix):
            yield blob_header.name

    async def drop(self) -> None:
        names = [name async for name in self.names()]
        for name in names:
            self.delete(name)

    async def delete_folder(self, folder_name: str) -> None:
        names = [name async for name in self.names() if name.startswith(folder_name)]
        for name in names:
            self.delete(name)

    async def insert_transactional(self, name: str, create_func: Callable[[str], Awaitable[Blob[T]]]) -> None:
        await self._upsert_transactional(name, create_func, None)

    async def update_transactional(self, name: str, update_func: Callable[[Blob[T]], Awaitable[Blob[T]]]) -> None:
        await self._upsert_transactional(name, None, update_func)

    async def upsert_transactional(
        self,
        name: str,
        create_func: Callable[[str], Awaitable[Blob[T]]],
        update_func: Callable[[Blob[T]], Awaitable[Blob[T]]],
    ) -> None:
        await self._upsert_transactional(name, create_func, update_func)

    async def _upsert_transactional(
        self,
        name: str,
        create_func: Optional[Callable[[str], Awaitable[Blob[T]]]] = None,
        update_func: Optional[Callable[[Blob[T]], Awaitable[Blob[T]]]] = None,
    ) -> None:
        # try:
        #     blob = await self.download_async(name)
        #     if update_func:
        #         updated_blob = await update_func(blob)
        #         await self.upload_async(updated_blob)
        #     else:
        #         raise KeyExistsException(self.collection_name, self.clazz, name)
        # except KeyNotExistsException as e:
        #     if not create_func:
        #         raise e
        #     created_blob = await create_func(name)
        #     await self.upload_async(created_blob)
        raise NotImplementedError("This method should be overridden if needed.")
