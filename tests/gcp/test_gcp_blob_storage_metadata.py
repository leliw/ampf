import logging

import pytest
import pytest_asyncio

from ampf.base import Blob
from ampf.base.blob_model import BaseBlobMetadata
from ampf.gcp import GcpAsyncBlobStorage, GcpAsyncFactory, GcpBlobStorage, GcpFactory

_log = logging.getLogger(__name__)

# Tests checking saving & reading non-ASCII blob metadata


class TestMetadata(BaseBlobMetadata):
    title: str


@pytest_asyncio.fixture
async def async_storage(gcp_async_factory: GcpAsyncFactory) -> GcpAsyncBlobStorage:  # type: ignore
    storage = gcp_async_factory.create_blob_storage("test_collection", TestMetadata)
    yield storage  # type: ignore
    await storage.drop()


@pytest.fixture
def storage(gcp_factory: GcpFactory) -> GcpBlobStorage:  # type: ignore
    storage = gcp_factory.create_blob_storage("test_collection", TestMetadata)
    yield storage  # type: ignore
    storage.drop()


@pytest.mark.asyncio
async def test_async_async(async_storage: GcpAsyncBlobStorage[TestMetadata]):
    # Given: Stored Blob with metadata with polish letters
    blob = Blob(
        name="test_blob", content="initial_data", metadata=TestMetadata(content_type="plain/text", title="łąźćóę")
    )
    await async_storage.upload_async(blob)
    # When: Blob is read
    downloaded_blob = await async_storage.download_async("test_blob")

    # Then: Metadata with polish letters is the same
    assert downloaded_blob.metadata.title == "łąźćóę"
    assert downloaded_blob.metadata.generation
    assert downloaded_blob.metadata.content_type == "plain/text"


@pytest.mark.asyncio
async def test_async_sync(async_storage: GcpAsyncBlobStorage[TestMetadata], storage: GcpBlobStorage[TestMetadata]):
    # Given: Stored Blob with metadata with polish letters
    blob = Blob(
        name="test_blob", content="initial_data", metadata=TestMetadata(content_type="plain/text", title="łąźćóę")
    )
    await async_storage.upload_async(blob)
    # When: Blob is read
    downloaded_blob = storage.download("test_blob")

    # Then: Metadata with polish letters is the same
    assert downloaded_blob.metadata.title == "łąźćóę"
    assert downloaded_blob.metadata.generation
    assert downloaded_blob.metadata.content_type == "plain/text"


@pytest.mark.asyncio
async def test_sync_async(storage: GcpBlobStorage[TestMetadata], async_storage: GcpAsyncBlobStorage[TestMetadata]):
    # Given: Stored Blob with metadata with polish letters
    blob = Blob(
        name="test_blob", content="initial_data", metadata=TestMetadata(content_type="plain/text", title="łąźćóę")
    )
    storage.upload(blob)
    # When: Blob is read
    downloaded_blob = await async_storage.download_async("test_blob")

    # Then: Metadata with polish letters is the same
    assert downloaded_blob.metadata.title == "łąźćóę"
    assert downloaded_blob.metadata.generation
    assert downloaded_blob.metadata.content_type == "plain/text"


def test_sync_sync(storage: GcpBlobStorage[TestMetadata]):
    # Given: Stored Blob with metadata with polish letters
    blob = Blob(
        name="test_blob", content="initial_data", metadata=TestMetadata(content_type="plain/text", title="łąźćóę")
    )
    storage.upload(blob)
    # When: Blob is read
    downloaded_blob = storage.download("test_blob")

    # Then: Metadata with polish letters is the same
    assert downloaded_blob.metadata.title == "łąźćóę"
    assert downloaded_blob.metadata.generation
    assert downloaded_blob.metadata.content_type == "plain/text"


@pytest.mark.asyncio
async def test_async_list_blobs(async_storage: GcpAsyncBlobStorage[TestMetadata]):
    # Given: Stored Blob with metadata with polish letters
    blob = Blob(
        name="test_blob_list",
        content="initial_data",
        metadata=TestMetadata(content_type="plain/text", title="łąźćóę"),
    )
    await async_storage.upload_async(blob)

    # When: list_blobs is called
    headers = []
    async for header in async_storage.list_blobs():
        headers.append(header)

    # Then: The metadata in the header is correctly unquoted
    assert len(headers) >= 1
    target_header = next(h for h in headers if h.name == "test_blob_list")
    assert target_header.metadata.title == "łąźćóę"


def test_sync_put_metadata(storage: GcpBlobStorage[TestMetadata]):
    # Given: Stored Blob with some metadata
    blob = Blob(
        name="test_blob_put_meta",
        content="initial_data",
        metadata=TestMetadata(content_type="plain/text", title="old_title"),
    )
    storage.upload(blob)

    # When: put_metadata is called with polish letters
    new_metadata = TestMetadata(content_type="plain/text", title="zażółć gęślą jaźń")
    storage.put_metadata("test_blob_put_meta", new_metadata)

    # Then: The metadata is updated and correctly unquoted when downloaded
    downloaded_blob = storage.download("test_blob_put_meta")
    assert downloaded_blob.metadata.title == "zażółć gęślą jaźń"


@pytest.mark.asyncio
async def test_async_put_metadata(async_storage: GcpAsyncBlobStorage[TestMetadata]):
    # Given: Stored Blob with some metadata
    blob = Blob(
        name="test_blob_put_meta_async",
        content="initial_data",
        metadata=TestMetadata(content_type="plain/text", title="old_title"),
    )
    await async_storage.upload_async(blob)

    # When: put_metadata is called with polish letters
    new_metadata = TestMetadata(content_type="plain/text", title="zażółć gęślą jaźń")
    await async_storage.put_metadata("test_blob_put_meta_async", new_metadata)

    # Then: The metadata is updated and correctly unquoted when downloaded
    downloaded_blob = await async_storage.download_async("test_blob_put_meta_async")
    assert downloaded_blob.metadata.title == "zażółć gęślą jaźń"
