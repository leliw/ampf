from uuid import UUID

import pytest
from pydantic import BaseModel

from ampf.base import BaseBlobMetadata, BlobCreate
from ampf.base.collection_def import CollectionDef
from ampf.base.exceptions import KeyNotExistsException
from ampf.cruds.crud_document_model import BaseDocument
from ampf.cruds.crud_document_service import CRUDDocumentService
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory


class TDocument(BaseDocument):
    pass


class TDocumentCreate(BaseModel):
    name: str
    content_type: str


class TDocumentUpdate(BaseModel):
    name: str | None = None
    content_type: str | None = None


class TDocumentHeader(BaseModel):
    id: UUID
    blob_name: str
    name: str
    content_type: str


class TMetadata(BaseBlobMetadata):
    pass


@pytest.fixture
def service() -> CRUDDocumentService:
    factory = InMemoryAsyncFactory(
        collection_defs=[
            CollectionDef("documents", TDocument),
        ]
    )

    storage = factory.get_collection(TDocument)
    blob_storage = factory.create_blob_storage("documents", TMetadata)

    return CRUDDocumentService(
        storage=storage,
        blob_storage=blob_storage,
        record_class=TDocument,
        metadata_class=TMetadata,
        header_class=TDocumentHeader,
        create_class=TDocumentCreate,
        update_class=TDocumentUpdate,
    )


def create_blob(content: str) -> BlobCreate:
    return BlobCreate(content=content)


async def test_get_headers_returns_empty_list(service: CRUDDocumentService):
    result = [header async for header in service.get_headers()]

    assert result == []


async def test_create_and_get_document(service: CRUDDocumentService):
    document_create = TDocumentCreate(
        name="document.txt",
        content_type="text/plain",
    )

    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=document_create,
    )

    assert isinstance(created.id, UUID)
    assert created.name == "document.txt"
    assert created.content_type == "text/plain"
    assert created.blob_name

    result = await service.get(created.id)

    assert result == created


async def test_create_document_is_available_in_headers(
    service: CRUDDocumentService,
):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    headers = [header async for header in service.get_headers()]

    assert len(headers) == 1
    assert headers[0].id == created.id
    assert headers[0].blob_name == created.blob_name
    assert headers[0].name == created.name
    assert headers[0].content_type == created.content_type


async def test_download_document(service: CRUDDocumentService):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    downloaded = await service.download(created.id)

    assert downloaded.content == b"Hello world"
    assert downloaded.name == created.name
    assert downloaded.metadata.content_type == created.content_type


async def test_create_blob_location(service: CRUDDocumentService):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    location = await service.create_blob_location(created.id)

    assert location.bucket == "__default__"
    assert location.name == f"documents/{created.blob_name}"


async def test_patch_document_updates_blob_metadata(
    service: CRUDDocumentService,
):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    updated = await service.patch(
        created.id,
        TDocumentUpdate(
            name="document.md",
            content_type="text/markdown",
        ),
    )

    assert updated.id == created.id
    assert updated.name == "document.md"
    assert updated.content_type == "text/markdown"

    downloaded = await service.download(created.id)

    assert downloaded.name == "document.md"
    assert downloaded.metadata.content_type == "text/markdown"


async def test_patch_document_with_empty_update_fails(
    service: CRUDDocumentService,
):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    with pytest.raises(ValueError, match="Update patch cannot be empty"):
        await service.patch(created.id, TDocumentUpdate())


async def test_delete_document_removes_record_and_blob(
    service: CRUDDocumentService,
):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    await service.delete(created.id)

    with pytest.raises(KeyNotExistsException):
        await service.get(created.id)

    with pytest.raises(KeyNotExistsException):
        await service.blob_service.download(created.blob_name)


async def test_get_headers_by_ids(service: CRUDDocumentService):
    first = await service.create(
        blob_create=create_blob("First"),
        value_create=TDocumentCreate(
            name="first.txt",
            content_type="text/plain",
        ),
    )
    second = await service.create(
        blob_create=create_blob("Second"),
        value_create=TDocumentCreate(
            name="second.txt",
            content_type="text/plain",
        ),
    )

    headers = [
        header
        async for header in service.get_headers([second.id, first.id])
    ]

    assert [header.id for header in headers] == [second.id, first.id]


async def test_get_headers_by_ids_ignores_missing_documents(
    service: CRUDDocumentService,
):
    created = await service.create(
        blob_create=create_blob("Hello world"),
        value_create=TDocumentCreate(
            name="document.txt",
            content_type="text/plain",
        ),
    )

    headers = [
        header
        async for header in service.get_headers([created.id, UUID(int=0)])
    ]

    assert len(headers) == 1
    assert headers[0].id == created.id
