import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ampf.base import BaseAsyncFactory, BlobHeader, KeyNotExistsException
from ampf.gcp.gcp_async_factory import GcpAsyncFactory
from ampf.in_memory import InMemoryAsyncFactory
from ampf.local import LocalAsyncFactory
from ampf.testing.api_test_client import ApiTestClient

# Test application source files
from .app.config import ServerConfig
from .app.dependencies import get_async_factory, get_server_config, lifespan
from .app.routers import files
from .app.routers.files import FileMetadata


@pytest.fixture
def config() -> ServerConfig:
    config = ServerConfig()
    return config


@pytest_asyncio.fixture(params=[InMemoryAsyncFactory, LocalAsyncFactory, GcpAsyncFactory])
async def async_factory(request, tmp_path):
    if request.param == LocalAsyncFactory:
        yield LocalAsyncFactory(tmp_path)
    elif request.param == GcpAsyncFactory:
        factory: GcpAsyncFactory = request.param(bucket_name="unit-tests-001")
        yield factory
        storage = factory.create_blob_storage("files")
        await storage.drop()
    else:
        yield request.param()


@pytest.fixture
def app(config, async_factory) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.dependency_overrides[get_server_config] = lambda: config
    app.dependency_overrides[get_async_factory] = lambda: async_factory

    @app.exception_handler(KeyNotExistsException)
    async def exception_not_found_callback(request: Request, exc: KeyNotExistsException):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    return app


@pytest.fixture
def client(app: FastAPI):
    app.include_router(router=files.router, prefix="/api/files")
    with ApiTestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_post_get_put_delete_file(client: ApiTestClient, async_factory: BaseAsyncFactory):
    # Test POST (Upload a file)
    file_content = "This is a test markdown document."
    file_name = "test_document.md"
    content_type = "text/markdown"
    files = {"file": (file_name, file_content, content_type)}
    blob_header = client.post_typed("/api/files", 200, BlobHeader[FileMetadata], files=files)
    assert blob_header

    # Verify file exists in storage
    async_storage = async_factory.create_blob_storage("files", FileMetadata)
    uploaded_blob = await async_storage.download_async(blob_header.name)
    assert uploaded_blob.name == blob_header.name
    assert uploaded_blob.metadata.content_type == content_type
    assert uploaded_blob.content.decode() == file_content

    # Test GET all documents
    all_documents = client.get_typed_list("/api/files", 200, BlobHeader[FileMetadata])
    assert len(all_documents) == 1
    assert all_documents[0].name == blob_header.name
    assert all_documents[0].metadata.content_type == content_type

    # Test GET a specific document content
    response = client.get(f"/api/files/{blob_header.name}", 200)
    assert response.headers["content-type"].startswith(content_type)
    assert response.content == file_content.encode()

    # Test DELETE the document
    response = client.delete(f"/api/files/{blob_header.name}", 200)

    # Verify file is deleted from disk
    with pytest.raises(KeyNotExistsException):
        uploaded_blob = await async_storage.download_async(blob_header.name)

    # Test GET after deletion (should be 404)
    client.get(f"/api/files/{blob_header.name}", 404)
