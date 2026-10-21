from collections.abc import AsyncGenerator

from ampf.base import BaseAsyncBlobStorage, BaseBlobMetadata, Blob, BlobHeader, BlobLocation


class CRUDBlobService[M: BaseBlobMetadata]:
    def __init__(self, blob_storage: BaseAsyncBlobStorage[M], metadata_class: type[M]) -> None:
        self.blob_storage = blob_storage
        self.metadata_class = metadata_class

    async def get_headers(self) -> AsyncGenerator[BlobHeader]:
        async for h in self.blob_storage.list_blobs():
            yield h

    async def upload(self, blob: Blob[M]) -> None:
        await self.blob_storage.upload_async(blob)

    async def download(self, blob_name: str) -> Blob[M]:
        return await self.blob_storage.download_async(blob_name)

    def create_blob_location(self, blob_name: str) -> BlobLocation:
        return self.blob_storage.create_blob_location(blob_name)

    async def get_metadata(self, blob_name: str) -> M:
        ret = await self.blob_storage.get_metadata(blob_name)
        if ret is None:
            raise ValueError(f"Metadata for blob '{blob_name}' not found")
        return ret

    async def put_metadata(self, blob_name: str, metadata: M) -> None:
        await self.blob_storage.put_metadata(blob_name, metadata)

    async def delete(self, blob_name: str) -> None:
        await self.blob_storage.delete_async(blob_name)
