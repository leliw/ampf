from datetime import datetime
import logging
from typing import Iterable
from uuid import UUID, uuid4

from ampf.base import BaseFactory, BaseAsyncFactory, Blob
from ampf.base.blob_model import BlobCreate
from .document_model import Document, DocumentCreate, DocumentHeader


class DocumentService:
    _log = logging.getLogger(__name__)

    def __init__(self, factory: BaseFactory, async_factory: BaseAsyncFactory):
        self.storage = factory.create_storage("documents", Document, key="id")
        self.blob_storage = async_factory.create_blob_storage("documents") # type: ignore

    async def post(self, blob: BlobCreate, document_create: DocumentCreate) -> Document:
        id=uuid4()
        now = datetime.now()
        name = f"{id}_{blob.name}"
        self._log.warning(name)
        await self.blob_storage.upload_async(Blob(name=name, data=blob.data, content_type=blob.content_type))
        document = Document(
            id=id,
            created_at=now,
            updated_at=now,
            **document_create.model_dump(),
        )
        self._log.warning(document)
        self.storage.save(document)
        return document

    def get_all(self) -> Iterable[DocumentHeader]:
        return [DocumentHeader(**v.model_dump()) for v in self.storage.get_all()]

    def get(self, key: UUID) -> Document:
        return self.storage.get(key)

    def put(self, key: UUID, value: Document) -> None:
        self.storage.put(key, value)

    def delete(self, key: UUID) -> None:
        self.storage.delete(key)
