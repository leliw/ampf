from pydantic import BaseModel
import pytest

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.blob_model import Blob, BlobLocation
from ampf.base.collection_def import CollectionDef
from ampf.gcp import GcpAsyncFactory
from ampf.in_memory import InMemoryAsyncFactory
from ampf.local import LocalAsyncFactory


@pytest.fixture(params=[InMemoryAsyncFactory, LocalAsyncFactory, GcpAsyncFactory])
def factory(request, tmp_path):
    if request.param == LocalAsyncFactory:
        factory = request.param(tmp_path)
    elif request.param == GcpAsyncFactory:
        factory = request.param(bucket_name="unit-tests-001")
    else:
        factory = request.param()
    return factory


class T(BaseModel):
    name: str


def test_create_storage(factory):
    storage = factory.create_storage("test", T, "name")

    assert storage is not None


def test_create_compact_storage(factory):
    storage = factory.create_compact_storage("test", T, "name")

    assert storage is not None


def test_create_blob_storage(factory):
    storage = factory.create_blob_storage(
        "test",
        T,
    )

    assert storage is not None


@pytest.mark.asyncio
async def test_upload_and_download_blob(factory):
    # Given: A blob and a blob location
    blob_location = BlobLocation(name="blob_test.txt")
    blob = Blob(name="blob_test.txt", content=b"test data")
    # When: A blob is uploaded
    await factory.upload_blob(blob_location, blob)
    # Then: It can be downloaded
    blob = await factory.download_blob(blob_location)
    assert blob.content == b"test data"


def test_create_blob_location(factory: BaseAsyncFactory):
    location = factory.create_blob_location("test/location")

    assert location is not None
    assert location.name == "test/location"


class D(BaseModel):
    name: str
    value: str


@pytest.mark.asyncio
async def test_register_and_get_collection(factory: BaseAsyncFactory):
    from ampf.base.exceptions import KeyNotExistsException

    # Given: A collection definition
    storage_def = CollectionDef("my_async_collection", D, "name")

    # When: The collection is registered
    factory.register_collections([storage_def])

    # Then: The collection can be retrieved by name
    storage = factory.get_collection("my_async_collection")
    assert storage is not None
    assert storage.decorated.collection_name == "my_async_collection"

    # And: The collection can be retrieved by type
    storage_by_type = factory.get_collection(D)
    assert storage_by_type is not None
    assert storage_by_type.decorated.collection_name == "my_async_collection"

    # And: Saving data works
    await storage.save(D(name="test", value="val"))
    assert (await storage.get("test")).value == "val"

    # And: Getting an unregistered collection raises an exception
    with pytest.raises(KeyNotExistsException):
        factory.get_collection("non_existent")

    # And: Getting an unregistered type raises an exception
    class UnregisteredModel(BaseModel):
        pass

    with pytest.raises(KeyNotExistsException):
        factory.get_collection(UnregisteredModel)
