from typing import Iterable

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ampf.base.exceptions import KeyNotExistsException
from ampf.local import LocalAsyncFactory

# Test application source files
from .app.config import ServerConfig
from .app.dependencies import get_async_factory, get_server_config, lifespan
from .app.routers import files


@pytest.fixture
def config() -> ServerConfig:
    config = ServerConfig()
    return config


@pytest.fixture
def local_async_factory(tmp_path):
    return LocalAsyncFactory(tmp_path)


@pytest.fixture
def app(config, local_async_factory) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.dependency_overrides[get_server_config] = lambda: config
    app.dependency_overrides[get_async_factory] = lambda: local_async_factory

    @app.exception_handler(KeyNotExistsException)
    async def exception_not_found_callback(request: Request, exc: KeyNotExistsException):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    return app


@pytest.fixture
def client(app: FastAPI) -> Iterable[TestClient]:
    app.include_router(router=files.router, prefix="/api/files")
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_post_get_put_delete_file(client: TestClient, local_async_factory: LocalAsyncFactory):
    # Test POST (Upload a file)
    file_content = "This is a test markdown document."
    file_name = "test_document.md"
    content_type = "text/markdown"
    files = {"file": (file_name, file_content, content_type)}
    response = client.post("/api/files", files=files)
    assert response.status_code == 200

    # Verify file exists in storage
    async_storage = local_async_factory.create_blob_storage("files")
    uploaded_blob = await async_storage.download_async(file_name)
    assert uploaded_blob.name == file_name
    assert uploaded_blob.content_type == content_type
    assert uploaded_blob.content.decode() == file_content

    # Test GET all documents
    response = client.get("/api/files")
    assert response.status_code == 200
    all_documents = response.json()
    assert len(all_documents) == 1
    assert all_documents[0]["name"] == file_name
    assert all_documents[0]["content_type"] == content_type

    # Test GET a specific document content
    response = client.get(f"/api/files/{file_name}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.content == file_content.encode()

    # Test DELETE the document
    response = client.delete(f"/api/files/{file_name}")
    assert response.status_code == 200

    # Verify file is deleted from disk
    with pytest.raises(KeyNotExistsException):
        uploaded_blob = await async_storage.download_async(file_name)

    # Test GET after deletion (should be 404)
    response = client.get(f"/api/files/{file_name}")
    assert response.status_code == 404
