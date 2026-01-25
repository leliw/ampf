import logging
from typing import AsyncGenerator

from ampf.base import BaseAsyncFactory, Blob
from ampf.base.blob_model import BaseBlobMetadata, BlobHeader, BlobLocation

_log = logging.getLogger(__name__)


class FileMetadata(BaseBlobMetadata):
    pass


class FileService:
    def __init__(self, async_factory: BaseAsyncFactory):
        self.blob_storage = async_factory.create_blob_storage("files", FileMetadata)

    async def upload_blob(self, blob: Blob[FileMetadata]) -> None:
        await self.blob_storage.upload_async(blob)

    async def download_blob(self, blob_location: BlobLocation) -> Blob[FileMetadata]:
        return await self.blob_storage.download_async(blob_location.name)

    async def get_all_files(self) -> AsyncGenerator[BlobHeader]:
        async for h in self.blob_storage.list_blobs():
            yield h

    def delete(self, file_name: str):
        self.blob_storage.delete(file_name)
