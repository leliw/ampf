import logging
from typing import Generator


from ampf.base import BaseAsyncFactory, Blob
from ampf.base.blob_model import BlobHeader, BlobLocation

_log = logging.getLogger(__name__)


class FileService:
    def __init__(self, async_factory: BaseAsyncFactory):
        self.blob_storage = async_factory.create_blob_storage("files")

    async def upload_blob(self, blob: Blob) -> None:
        await self.blob_storage.upload_async(blob)

    async def download_blob(self, blob_location: BlobLocation) -> Blob:
        return await self.blob_storage.download_async(blob_location.name)

    def get_all_files(self) -> Generator[BlobHeader]:
        yield from self.blob_storage.list_blobs()

    def delete(self, file_name: str):
        self.blob_storage.delete(file_name)
