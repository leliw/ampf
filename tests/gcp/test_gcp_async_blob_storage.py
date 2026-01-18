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
def storage(gcp_async_factory: GcpAsyncFactory) -> BaseAsyncBlobStorage[SampleMetadata]:  # type: ignore
    storage = gcp_async_factory.create_blob_storage("test_collection", SampleMetadata)
    yield storage  # type: ignore
    storage.drop()


@pytest.mark.asyncio
async def test_update_transactional_one_thread(storage: BaseAsyncBlobStorage):
    blob = Blob(name="test_blob", content=b"initial_data")
    await storage.upload_async(blob)

    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, content=b.content + b"_updated", content_type=b.content_type)

    await storage.update_transactional("test_blob", update_func)

    updated_blob = await storage.download_async("test_blob")
    assert updated_blob.content == b"initial_data_updated"


@pytest.mark.asyncio
async def test_update_transactional_two_threads(storage: BaseAsyncBlobStorage):
    blob = Blob(name="test_blob", content=b"initial_data")
    await storage.upload_async(blob)

    async def update_func1(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        print("Update func1 started")
        await asyncio.sleep(0.1)  # Simulate some processing delay
        print("Update func1 completed")
        return Blob(name=b.name, content=b.content + b"_updated1")

    async def update_func2(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        print("Update func2 completed")
        return Blob(name=b.name, content=b.content + b"_updated2")

    await asyncio.gather(
        storage.update_transactional("test_blob", update_func1),
        storage.update_transactional("test_blob", update_func2),
    )
    updated_blob = await storage.download_async("test_blob")
    assert (
        updated_blob.content == b"initial_data_updated2_updated1"
        or updated_blob.content == b"initial_data_updated1_updated2"
    )


@pytest.mark.asyncio
async def test_update_transactional_non_existent_blob(storage: BaseAsyncBlobStorage):
    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, content=b.content + b"_updated")

    with pytest.raises(KeyNotExistsException):
        await storage.update_transactional("non_existent_blob", update_func)


# ----- upsert_transactional


async def create_func(name: str) -> Blob[SampleMetadata]:
    return Blob(name=name, content=b"new_data")


async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
    return Blob(name=b.name, content=b.content + b"_updated")


@pytest.mark.asyncio
async def test_upsert_transactional_creates_new_blob(storage: BaseAsyncBlobStorage):
    # Given: create & update functions
    assert create_func
    assert update_func
    # When: Create new blob
    await storage.upsert_transactional("new_blob", create_func, update_func)
    # Then: Blob is created
    created_blob = await storage.download_async("new_blob")
    assert created_blob.content == b"new_data"


@pytest.mark.asyncio
async def test_upsert_transactional_updates_existing_blob(storage: BaseAsyncBlobStorage):
    # Given: create & update functions
    assert create_func
    assert update_func
    # And: A stored blob
    blob = Blob(name="existing_blob", content=b"initial_data")
    await storage.upload_async(blob)
    # When: Update existing blob
    await storage.upsert_transactional("existing_blob", create_func, update_func)
    # Then: Blob is updated
    updated_blob = await storage.download_async("existing_blob")
    assert updated_blob.content == b"initial_data_updated"


@pytest.mark.asyncio
async def test_upsert_transactional_concurrent_creation(storage: BaseAsyncBlobStorage):
    # Two coroutines try to create the same blob. One will create, the other will update.

    async def create_func1(name: str) -> Blob[SampleMetadata]:
        await asyncio.sleep(0.1)  # Simulate some processing delay
        return Blob(name=name, content=b"created1")

    async def create_func2(name: str) -> Blob[SampleMetadata]:
        return Blob(name=name, content=b"created2")

    async def update_func1(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        await asyncio.sleep(0.1)  # Simulate some processing delay
        return Blob(name=b.name, content=b.content + b"_updated1")

    async def update_func2(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, content=b.content + b"_updated2")

    await asyncio.gather(
        storage.upsert_transactional("concurrent_blob", create_func1, update_func1),
        storage.upsert_transactional("concurrent_blob", create_func2, update_func2),
    )

    final_blob = await storage.download_async("concurrent_blob")
    # The final result depends on which function executed first on the final successful write
    assert final_blob.content == b"created2_updated1" or final_blob.content == b"created1_updated2"
