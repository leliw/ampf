from pathlib import Path
from typing import Iterable

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ampf.base.exceptions import KeyNotExistsException
from ampf.local.local_factory import LocalFactory
from ampf.local_async.async_local_factory import AsyncLocalFactory

# Test application source files
from .app.config import ServerConfig
from .app.dependencies import get_async_factory, get_factory, get_server_config, lifespan
from .app.features.documents.document_model import Document, DocumentCreate, DocumentHeader, DocumentPatch
from .app.routers import documents


@pytest.fixture
def config() -> ServerConfig:
    config = ServerConfig()
    return config


@pytest.fixture
def local_factory(tmp_path):
    return LocalFactory(tmp_path)


@pytest.fixture
def local_async_factory(tmp_path):
    return AsyncLocalFactory(tmp_path / "blobs")


@pytest.fixture
def app(config, local_factory, local_async_factory) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.dependency_overrides[get_server_config] = lambda: config
    app.dependency_overrides[get_factory] = lambda: local_factory
    app.dependency_overrides[get_async_factory] = lambda: local_async_factory

    @app.exception_handler(KeyNotExistsException)
    async def exception_not_found_callback(request: Request, exc: KeyNotExistsException):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    return app


@pytest.fixture
def client(app: FastAPI) -> Iterable[TestClient]:
    app.include_router(router=documents.router, prefix="/api/documents")
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_post_get_put_delete_document(client: TestClient, local_async_factory: AsyncLocalFactory):
    # Test POST (Upload a document)
    file_content = "This is a test markdown document."
    file_name = "test_document.md"
    content_type = "text/markdown"
    files = {"file": (file_name, file_content, content_type)}
    document_create = DocumentCreate(name=file_name, content_type=content_type)
    response = client.post("/api/documents", files=files, data=document_create.model_dump())
    assert response.status_code == 200
    uploaded_document_header = DocumentHeader(**response.json())
    assert uploaded_document_header.name == file_name
    assert uploaded_document_header.content_type
    assert uploaded_document_header.content_type.startswith(content_type)
    document_id = uploaded_document_header.id

    # Verify file exists in storage
    async_storage = local_async_factory.create_blob_storage("documents")
    uploaded_blob = await async_storage.download_async(f"{document_id}")
    assert uploaded_blob.name == f"{document_id}"
    assert uploaded_blob.content_type == content_type
    assert uploaded_blob.data.read().decode() == file_content

    # Test GET all documents
    response = client.get("/api/documents")
    assert response.status_code == 200
    all_documents = response.json()
    assert len(all_documents) == 1
    assert all_documents[0]["id"] == str(document_id)
    assert all_documents[0]["name"] == file_name
    assert all_documents[0]["content_type"] == content_type

    # Test GET a specific document content
    response = client.get(f"/api/documents/{document_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.content == file_content.encode()

    # Test GET a specific document metadata
    response = client.get(f"/api/documents/{document_id}/metadata")
    assert response.status_code == 200
    document = response.json()
    assert document["id"] == str(document_id)
    assert document["name"] == file_name
    assert document["content_type"].startswith("text/markdown")

    # Test PUT (Update the document)
    updated_file_content = "This is the updated content for the document."
    updated_file_name = "updated_document.txt"
    updated_content_type = "text/plain"
    updated_files = {"file": (updated_file_name, updated_file_content, updated_content_type)}
    document_patch = DocumentPatch(name=updated_file_name, content_type=updated_content_type)
    response = client.put(f"/api/documents/{document_id}", files=updated_files, data=document_patch.model_dump())
    assert response.status_code == 200
    updated_document = Document(**response.json())
    assert updated_document.name == updated_file_name
    assert updated_document.content_type
    assert updated_document.content_type.startswith(updated_content_type)
    assert updated_document.id == document_id  # ID should remain the same

    updated_blob = await async_storage.download_async(f"{document_id}")
    assert updated_blob.name == f"{document_id}"
    assert updated_blob.content_type == updated_content_type
    assert updated_blob.data.read().decode() == updated_file_content

    # Test GET the updated document
    response = client.get(f"/api/documents/{document_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(updated_content_type)
    assert response.headers["content-disposition"] == f'attachment; filename="{updated_file_name}"'
    assert response.content.decode() == updated_file_content

    # Test PATCH metadata
    patched_file_name = "patched_document.txt"
    document_patch = DocumentPatch(name=patched_file_name)
    response = client.patch(f"/api/documents/{document_id}", json=document_patch.model_dump())
    assert response.status_code == 200
    patched_document = Document(**response.json())
    assert patched_document.name == patched_file_name
    assert patched_document.content_type
    assert patched_document.content_type.startswith(updated_content_type)
    assert patched_document.id == document_id  # ID should remain the same

    # Test GET the patched document
    response = client.get(f"/api/documents/{document_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(updated_content_type)
    assert response.headers["content-disposition"] == f'attachment; filename="{patched_file_name}"'
    assert response.content.decode() == updated_file_content

    # Test DELETE the document
    response = client.delete(f"/api/documents/{document_id}")
    assert response.status_code == 200

    # Verify file is deleted from disk
    with pytest.raises(KeyNotExistsException):
        uploaded_blob = await async_storage.download_async(f"{document_id}_{updated_file_name}")

    # Test GET after deletion (should be 404)
    response = client.get(f"/api/documents/{document_id}")
    assert response.status_code == 404
