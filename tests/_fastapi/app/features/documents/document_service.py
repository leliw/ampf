from datetime import datetime
import logging
from typing import Iterable
from uuid import UUID, uuid4

from ampf.base import BaseFactory, BaseAsyncFactory, Blob
from ampf.base.blob_model import BlobCreate
from .document_model import Document, DocumentCreate, DocumentHeader, DocumentPatch


class DocumentService:
    _log = logging.getLogger(__name__)

    def __init__(self, factory: BaseFactory, async_factory: BaseAsyncFactory):
        self.storage = factory.create_storage("documents", Document, key="id")
        self.blob_storage = async_factory.create_blob_storage("documents") # type: ignore

    async def post(self, blob: BlobCreate, document_create: DocumentCreate) -> Document:
        id=uuid4()
        now = datetime.now()
        document = Document(
            id=id,
            created_at=now,
            updated_at=now,
            **document_create.model_dump(),
        )
        name = f"{id}_{document_create.name}"
        await self.blob_storage.upload_async(Blob(name=name, data=blob.data, content_type=blob.content_type))
        self.storage.save(document)
        return document

    def get_all(self) -> Iterable[DocumentHeader]:
        return [DocumentHeader(**v.model_dump()) for v in self.storage.get_all()]

    def get_meta(self, key: UUID) -> Document:
        return self.storage.get(key)

    async def get(self, key: UUID) -> Blob:
        document = self.storage.get(key)
        name = f"{document.id}_{document.name}"
        blob = await self.blob_storage.download_async(name)
        blob.name = document.name
        return blob

    


    def patch(self, id: UUID, document_patch: DocumentPatch) -> Document:
        document = self.storage.get(id)
        patch_dict = document_patch.model_dump(exclude_unset=True, exclude_none=True)
        document.__dict__.update(patch_dict)
        document.updated_at = datetime.now()
        self.storage.put(id, document)
        return document

    async def put(self, id: UUID, blob: BlobCreate, document_patch: DocumentPatch) -> Document:
        old_document = self.storage.get(id)
        document = self.patch(id, document_patch)
        old_name = f"{old_document.id}_{old_document.name}"
        name = f"{id}_{document.name}"
        if old_name != name:
            self.blob_storage.delete(old_name)
        await self.blob_storage.upload_async(Blob(name=name, data=blob.data, content_type=blob.content_type))
        return document

    def delete(self, key: UUID) -> None:
        self.storage.delete(key)
