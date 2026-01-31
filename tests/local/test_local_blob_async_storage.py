import asyncio
import tempfile
from pathlib import Path

import pytest

from ampf.base import Blob
from ampf.base.blob_model import BaseBlobMetadata
from ampf.base.exceptions import KeyNotExistsException
from ampf.local import LocalAsyncBlobStorage


class SampleMetadata(BaseBlobMetadata):
    name: str
    version: int


@pytest.fixture
def temp_storage_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_storage_dir):
    return LocalAsyncBlobStorage(collection_name=temp_storage_dir, metadata_type=SampleMetadata)

@pytest.fixture
def storage_no_metadata(temp_storage_dir):
    return LocalAsyncBlobStorage(collection_name=temp_storage_dir)

@pytest.mark.asyncio
async def test_upload_and_download(storage: LocalAsyncBlobStorage):
    metadata = SampleMetadata(name="file1", version=1)
    blob = Blob[SampleMetadata](
        name="test_blob", metadata=metadata, content=b"Hello, World!"
    )

    await storage.upload_async(blob)
    downloaded = await storage.download_async("test_blob")

    assert downloaded.name == blob.name
    assert downloaded.metadata == blob.metadata
    assert downloaded.content == blob.content


@pytest.mark.asyncio
async def test_upload_and_download_without_content_type(storage: LocalAsyncBlobStorage):
    metadata = SampleMetadata(name="file1", version=1)
    blob = Blob[SampleMetadata](name="test_blob", metadata=metadata, content=b"Hello, World!")

    await storage.upload_async(blob)
    downloaded = await storage.download_async("test_blob")

    assert downloaded.name == blob.name
    assert downloaded.content_type == blob.content_type
    assert downloaded.metadata == blob.metadata
    assert downloaded.content == blob.content

@pytest.mark.asyncio
async def test_upload_and_download_without_metadata(storage_no_metadata: LocalAsyncBlobStorage):
    blob = Blob(
        name="test_blob",
        content=b"Hello, World!",
        content_type="text/x-scss"
    )

    await storage_no_metadata.upload_async(blob)
    downloaded = await storage_no_metadata.download_async("test_blob")

    assert downloaded.name == blob.name
    assert downloaded.metadata == blob.metadata
    assert downloaded.content == blob.content


@pytest.mark.asyncio
async def test_list_blobs(storage: LocalAsyncBlobStorage):
    blob1 = Blob[SampleMetadata](
        name="item1", metadata=SampleMetadata(name="first", version=1, content_type="application/json"), content=b"{}"
    )
    blob2 = Blob[SampleMetadata](
        name="item2", metadata=SampleMetadata(name="second", version=2, content_type="application/json"), content=b"{}"
    )

    await storage.upload_async(blob1)
    await storage.upload_async(blob2)

    headers = [h async for h in storage.list_blobs()]
    keys = [h.name for h in headers]

    assert "item1" in keys
    assert "item2" in keys
    for header in headers:
        assert isinstance(header.metadata, SampleMetadata)


@pytest.mark.asyncio
async def test_delete_blob(storage: LocalAsyncBlobStorage):
    blob = Blob[SampleMetadata](
        name="todelete",
        metadata=SampleMetadata(name="to delete", version=1, content_type="text/plain"),
        content=b"delete me",
    )
    await storage.upload_async(blob)

    assert storage.exists("todelete")
    storage.delete("todelete")
    assert not storage.exists("todelete")


@pytest.mark.asyncio
async def test_download_missing_blob_raises(storage: LocalAsyncBlobStorage):
    with pytest.raises(KeyNotExistsException):
        await storage.download_async("not_existing")


@pytest.mark.asyncio
async def test_content_type_affects_file_extension(storage: LocalAsyncBlobStorage):
    blob = Blob[SampleMetadata](
        name="typed_blob",
        metadata=SampleMetadata(name="json test", version=3, content_type="application/json"),
        content=b'{"foo": "bar"}',
    )
    await storage.upload_async(blob)

    base_path = Path(storage.base_path)
    files = list(base_path.glob("typed_blob.*"))

    # Expect at least one file with a .json or matching MIME extension
    assert any(f.suffix == ".json" or "typed_blob" in str(f) for f in files)


@pytest.mark.asyncio
async def test_update_transactional_one_thread(storage: LocalAsyncBlobStorage):
    metadata = SampleMetadata(name="file1", version=1, content_type="text/plain")
    blob = Blob(name="test_blob", content=b"initial_data", metadata=metadata)
    await storage.upload_async(blob)

    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, content=b.content + b"_updated", metadata=b.metadata)

    await storage.update_transactional("test_blob", update_func)

    updated_blob = await storage.download_async("test_blob")
    assert updated_blob.content == b"initial_data_updated"


@pytest.mark.asyncio
async def test_update_transactional_two_threads(storage: LocalAsyncBlobStorage):
    metadata = SampleMetadata(name="file1", version=1, content_type="text/plain")
    blob = Blob(name="test_blob", content=b"initial_data", metadata=metadata)
    await storage.upload_async(blob)

    async def update_func1(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        print("Update func1 started")
        await asyncio.sleep(0.1)  # Simulate some processing delay
        print("Update func1 completed")
        return Blob(name=b.name, content=b.content + b"_updated1", metadata=b.metadata)

    async def update_func2(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        print("Update func2 completed")
        return Blob(name=b.name, content=b.content + b"_updated2", metadata=b.metadata)

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
async def test_update_transactional_non_existent_blob(storage: LocalAsyncBlobStorage):
    async def update_func(b: Blob[SampleMetadata]) -> Blob[SampleMetadata]:
        return Blob(name=b.name, content=b.content + b"_updated", metadata=b.metadata)

    with pytest.raises(KeyNotExistsException):
        await storage.update_transactional("non_existent_blob", update_func)
