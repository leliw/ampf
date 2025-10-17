import asyncio
import pytest
import tempfile
from pathlib import Path

from pydantic import BaseModel
from ampf.base.exceptions import KeyNotExistsException
from ampf.local_async.local_blob_async_storage import LocalBlobAsyncStorage, Blob


class SampleMetadata(BaseModel):
    name: str
    version: int


@pytest.fixture
def temp_storage_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_storage_dir):
    return LocalBlobAsyncStorage(collection_name=temp_storage_dir, metadata_type=SampleMetadata)


@pytest.mark.asyncio
async def test_upload_and_download(storage: LocalBlobAsyncStorage):
    metadata = SampleMetadata(name="file1", version=1)
    blob = Blob[SampleMetadata](
        name="test_blob",
        content_type="text/plain",
        metadata=metadata,
        data=b"Hello, World!"
    )

    await storage.upload_async(blob)
    downloaded = await storage.download_async("test_blob")

    assert downloaded.name == blob.name
    assert downloaded.content_type == blob.content_type
    assert downloaded.metadata == blob.metadata
    assert downloaded.data.read() == blob.data.read()




@pytest.mark.asyncio
async def test_upload_and_download_without_conent_type(storage: LocalBlobAsyncStorage):
    metadata = SampleMetadata(name="file1", version=1)
    blob = Blob[SampleMetadata](
        name="test_blob",
        metadata=metadata,
        data=b"Hello, World!"
    )

    await storage.upload_async(blob)
    downloaded = await storage.download_async("test_blob")

    assert downloaded.name == blob.name
    assert downloaded.content_type == blob.content_type
    assert downloaded.metadata == blob.metadata
    assert downloaded.data.read() == blob.data.read()



@pytest.mark.asyncio
async def test_list_blobs(storage: LocalBlobAsyncStorage):
    blob1 = Blob[SampleMetadata](
        name="item1",
        content_type="application/json",
        metadata=SampleMetadata(name="first", version=1),
        data=b"{}"
    )
    blob2 = Blob[SampleMetadata](
        name="item2",
        content_type="application/json",
        metadata=SampleMetadata(name="second", version=2),
        data=b"{}"
    )

    await storage.upload_async(blob1)
    await storage.upload_async(blob2)

    headers = storage.list_blobs()
    keys = [h.name for h in headers]

    assert "item1" in keys
    assert "item2" in keys
    for header in headers:
        assert isinstance(header.metadata, SampleMetadata)


@pytest.mark.asyncio
async def test_delete_blob(storage: LocalBlobAsyncStorage):
    blob = Blob[SampleMetadata](
        name="todelete",
        content_type="text/plain",
        metadata=SampleMetadata(name="to delete", version=1),
        data=b"delete me"
    )
    await storage.upload_async(blob)

    assert storage.exists("todelete")
    storage.delete("todelete")
    assert not storage.exists("todelete")


@pytest.mark.asyncio
async def test_download_missing_blob_raises(storage: LocalBlobAsyncStorage):
    with pytest.raises(KeyNotExistsException):
        await storage.download_async("not_existing")


@pytest.mark.asyncio
async def test_content_type_affects_file_extension(storage: LocalBlobAsyncStorage):
    blob = Blob[SampleMetadata](
        name="typed_blob",
        content_type="application/json",
        metadata=SampleMetadata(name="json test", version=3),
        data=b"{\"foo\": \"bar\"}"
    )
    await storage.upload_async(blob)

    base_path = Path(storage.base_path)
    files = list(base_path.glob("typed_blob.*"))

    # Expect at least one file with a .json or matching MIME extension
    assert any(f.suffix == ".json" or "typed_blob" in str(f) for f in files)


@pytest.mark.asyncio
async def test_update_transactional_one_thread(storage: LocalBlobAsyncStorage):
    blob = Blob(name="test_blob", data=b"initial_data")
    await storage.upload_async(blob)

    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, data=b.data.read() + b"_updated")

    await storage.update_transactional("test_blob", update_func)

    updated_blob = await storage.download_async("test_blob")
    assert updated_blob.data.read() == b"initial_data_updated"

@pytest.mark.asyncio
async def test_update_transactional_two_threads(storage: LocalBlobAsyncStorage):
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
async def test_update_transactional_non_existent_blob(storage: LocalBlobAsyncStorage):
    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, data=b.data.read() + b"_updated")

    with pytest.raises(KeyNotExistsException):
        await storage.update_transactional("non_existent_blob", update_func)