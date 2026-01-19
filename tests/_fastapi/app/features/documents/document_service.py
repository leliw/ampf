import asyncio
import logging
from typing import AsyncGenerator
from uuid import UUID

from ampf.base import BaseAsyncFactory, Blob
from ampf.base.blob_model import BlobCreate

from .document_model import Document, DocumentCreate, DocumentPatch


class DocumentService:
    _log = logging.getLogger(__name__)

    def __init__(self, async_factory: BaseAsyncFactory):
        self.storage = async_factory.create_storage("documents", Document, key="id")
        self.blob_storage = async_factory.create_blob_storage("documents")  # type: ignore

    async def post(self, document_create: DocumentCreate, blob_create: BlobCreate) -> Document:
        document = Document.create(document_create)
        blob = Blob.create(blob_create)
        blob.name = str(document.id)
        await asyncio.gather(
            self.storage.save(document),
            self.blob_storage.upload_async(blob),
        )
        return document

    async def get_all(self) -> AsyncGenerator[Document]:
        async for document in self.storage.get_all():
            yield document

    async def get_meta(self, id: UUID) -> Document:
        return await self.storage.get(id)

    async def get(self, id: UUID) -> Blob:
        document = await self.storage.get(id)
        blob = await self.blob_storage.download_async(str(id))
        blob.name = document.name
        return blob

    async def patch(self, id: UUID, document_patch: DocumentPatch) -> Document:
        return await self.storage.patch(id, document_patch)

    async def put(self, id: UUID, blob_create: BlobCreate, document_patch: DocumentPatch) -> Document:
        document = await self.patch(id, document_patch)
        blob = Blob.create(blob_create)
        blob.name = str(id)
        self.blob_storage.delete(str(id))
        await self.blob_storage.upload_async(blob)
        return document

    async def delete(self, id: UUID) -> None:
        self.blob_storage.delete(str(id))
        await self.storage.delete(id)
