import pytest
import pytest_asyncio

from ampf.base.blob_model import BaseBlobMetadata
from ampf.gcp import GcpAsyncBlobStorage, GcpAsyncFactory, GcpBlobStorage, GcpFactory


@pytest_asyncio.fixture
async def async_storage(gcp_async_factory: GcpAsyncFactory) -> GcpAsyncBlobStorage:  # type: ignore
    storage = gcp_async_factory.create_blob_storage("test_collection", BaseBlobMetadata)
    yield storage  # type: ignore
    await storage.drop()


@pytest.fixture
def storage(gcp_factory: GcpFactory) -> GcpBlobStorage:  # type: ignore
    storage = gcp_factory.create_blob_storage("test_collection", BaseBlobMetadata)
    yield storage  # type: ignore
    storage.drop()


def test_create_blob_location_with_bucket(storage: GcpBlobStorage):
    # When: Create blob location
    blob_location = storage.create_blob_location("test_blob")
    # Then: Blob location is created
    assert blob_location.name == "test_collection/test_blob"
    assert blob_location.bucket == "unit-tests-001"


def test_create_blob_location_with_bucket_async(async_storage: GcpAsyncBlobStorage):
    # When: Create blob location
    blob_location = async_storage.create_blob_location("test_blob")
    # Then: Blob location is created
    assert blob_location.name == "test_collection/test_blob"
    assert blob_location.bucket == "unit-tests-001"
