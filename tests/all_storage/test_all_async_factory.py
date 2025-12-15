from pydantic import BaseModel
import pytest

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.blob_model import Blob, BlobLocation
from ampf.gcp import GcpAsyncFactory
from ampf.in_memory import InMemoryAsyncFactory
from ampf.local_async import AsyncLocalFactory


@pytest.fixture(params=[InMemoryAsyncFactory, AsyncLocalFactory, GcpAsyncFactory])
def factory(request, tmp_path):
    if request.param == AsyncLocalFactory:
        factory = request.param(tmp_path)
    elif request.param == GcpAsyncFactory:
        factory = request.param(bucket_name='unit-tests-001')
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
    storage = factory.create_blob_storage("test", T, )

    assert storage is not None


@pytest.mark.asyncio
async def test_upload_and_download_blob(factory):
    # Given: A blob and a blob location
    blob_location = BlobLocation(name="blob_test.txt")
    blob = Blob(name="blob_test.txt", data=b"test data")
    # When: A blob is uploaded
    await factory.upload_blob(blob_location, blob)
    # Then: It can be downloaded
    blob = await factory.download_blob(blob_location)
    assert blob.content == b"test data"



def test_create_blob_location(factory: BaseAsyncFactory):
    location = factory.create_blob_location("test/location")

    assert location is not None
    assert location.name == "test/location"