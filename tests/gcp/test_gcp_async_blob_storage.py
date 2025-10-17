import asyncio
import logging

import pytest
from pydantic import BaseModel

from ampf.base.base_async_blob_storage import BaseAsyncBlobStorage
from ampf.base.blob_model import Blob
from ampf.base.exceptions import KeyNotExistsException
from ampf.gcp.gcp_async_factory import GcpAsyncFactory

_log = logging.getLogger(__name__)


class SampleMetadata(BaseModel):
    description: str


@pytest.fixture
def storage(gcp_async_factory: GcpAsyncFactory) -> BaseAsyncBlobStorage[SampleMetadata]: # type: ignore
    storage = gcp_async_factory.create_blob_storage("test_collection", SampleMetadata)
    yield storage # type: ignore
    storage.drop()


@pytest.mark.asyncio
async def test_update_transactional_one_thread(storage: BaseAsyncBlobStorage):
    blob = Blob(name="test_blob", data=b"initial_data")
    await storage.upload_async(blob)

    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, data=b.data.read() + b"_updated", content_type=b.content_type)

    await storage.update_transactional("test_blob", update_func)

    updated_blob = await storage.download_async("test_blob")
    assert updated_blob.data.read() == b"initial_data_updated"


@pytest.mark.asyncio
async def test_update_transactional_two_threads(storage: BaseAsyncBlobStorage):
    blob = Blob(name="test_blob", data=b"initial_data")
    await storage.upload_async(blob)

    async def update_func1(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        print("Update func1 started")
        await asyncio.sleep(0.1)  # Simulate some processing delay
        print("Update func1 completed")
        return Blob(name=b.name, data=b.data.read() + b"_updated1")

    async def update_func2(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        print("Update func2 completed")
        return Blob(name=b.name, data=b.data.read() + b"_updated2")

    await asyncio.gather(
        storage.update_transactional("test_blob", update_func1),
        storage.update_transactional("test_blob", update_func2),
    )
    updated_blob = await storage.download_async("test_blob")
    assert (
        updated_blob.data.read() == b"initial_data_updated2_updated1"
        or updated_blob.data.read() == b"initial_data_updated1_updated2"
    )


@pytest.mark.asyncio
async def test_update_transactional_non_existent_blob(storage: BaseAsyncBlobStorage):
    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, data=b.data.read() + b"_updated")

    with pytest.raises(KeyNotExistsException):
        await storage.update_transactional("non_existent_blob", update_func)
