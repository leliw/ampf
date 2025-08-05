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
from .app.features.documents.document_model import DocumentCreate, DocumentHeader
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


def test_post_get_put_delete_document(client: TestClient, tmp_path: Path):
    # Test POST (Upload a document)
    file_content = "This is a test markdown document."
    file_name = "test_document.md"
    files = {"file": (file_name, file_content, "text/markdown")}
    document_create = DocumentCreate(name=file_name, content_type="text/markdown")
    d = document_create.model_dump()
    print(d)
    response = client.post("/api/documents", files=files, data=d)
    print(response.json())
    assert response.status_code == 200
    uploaded_document_header = DocumentHeader(**response.json())
    assert uploaded_document_header.name == file_name
    assert uploaded_document_header.content_type
    assert uploaded_document_header.content_type.startswith("text/markdown")
    document_id = uploaded_document_header.id

    # Verify file exists on disk
    expected_storage_path = tmp_path / f"blobs/documents/{document_id}_{file_name}"
    print(expected_storage_path)
    assert expected_storage_path.exists()
    assert expected_storage_path.read_text() == file_content