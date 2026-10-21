import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

from pydantic import BaseModel, TypeAdapter

from ampf.base import BaseAsyncBlobStorage, BaseAsyncCollectionStorage, BaseBlobMetadata, Blob, BlobCreate, BlobLocation

from .crud_blob_service import CRUDBlobService
from .crud_document_model import BaseDocument
from .crud_service import CRUDService


class CRUDDocumentService[R: BaseDocument, M: BaseBlobMetadata, H: BaseModel, C: BaseModel, U: BaseModel]:
    def __init__(
        self,
        storage: BaseAsyncCollectionStorage[R],
        blob_storage: BaseAsyncBlobStorage[M],
        record_class: type[R] | TypeAdapter[R],
        metadata_class: type[M],
        header_class: type[H],
        create_class: type[C],
        update_class: type[U] | None = None,
    ) -> None:
        self.service = CRUDService(storage, record_class, header_class, create_class, update_class)
        self.blob_service = CRUDBlobService(blob_storage, metadata_class)

    def record_to_metadata(self, value: R) -> M:
        dict_value = value.model_dump()
        return self.blob_service.metadata_class.model_validate(dict_value, extra="ignore")

    def create_to_blob_record(self, blob_create: BlobCreate, value_create: C) -> tuple[Blob[M], R]:
        record = self.service.create_to_record(value_create)
        metadata = self.record_to_metadata(record)
        blob = Blob[M].create(blob_create, metadata)
        blob.name = record.blob_name
        return blob, record

    async def create(self, blob_create: BlobCreate, value_create: C) -> R:
        blob, value = self.create_to_blob_record(blob_create, value_create)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.blob_service.upload(blob))
            tg.create_task(self.service.create(value))
        return value

    async def create_blob_location(self, id: UUID) -> BlobLocation:
        document = await self.service.get(id)
        return self.blob_service.create_blob_location(document.blob_name)

    async def download(self, id: UUID) -> Blob[M]:
        document = await self.service.get(id)
        ret = await self.blob_service.download(document.blob_name)
        ret.name = document.name
        return ret

    async def patch(self, id: UUID, document_patch: U) -> R:
        old_document = await self.service.get(id)
        try:
            async with asyncio.TaskGroup() as tg:
                t1 = tg.create_task(self.service.update(id, document_patch))
                t2 = tg.create_task(self.blob_service.get_metadata(old_document.blob_name))
        except* ValueError as exception_group:
            raise exception_group.exceptions[0]
        new_document = t1.result()
        old_metadata = t2.result()
        if old_metadata:
            new_metadata = old_metadata.model_copy(
                update=self.record_to_metadata(new_document).model_dump(exclude_unset=True)
            )
            if new_metadata != old_metadata:
                await self.blob_service.put_metadata(old_document.blob_name, new_metadata)
        return new_document

    async def delete(self, id: UUID) -> None:
        document = await self.service.get(id)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.service.delete(id))
            tg.create_task(self.blob_service.delete(document.blob_name))

    async def get(self, id: UUID) -> R:
        return await self.service.get(id)

    async def get_headers(self, ids: list[UUID] | None = None) -> AsyncGenerator[H]:
        async for h in self.service.get_headers(ids):
            yield h
