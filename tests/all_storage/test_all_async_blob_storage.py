import os
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from ampf.base import BaseAsyncBlobStorage, BaseBlobStorage, KeyNotExistsException

# from ampf.gcp import GcpBlobStorage
from ampf.base.blob_model import Blob
from ampf.gcp import GcpAsyncBlobStorage
from ampf.in_memory import InMemoryBlobAsyncStorage

# from ampf.local import LocalBlobStorage


class MyMetadata(BaseModel):
    name: str = Field(...)
    age: int = Field(...)


@pytest.fixture(params=[GcpAsyncBlobStorage])
def storage(gcp_factory, request, tmp_path):
    # if request.param == LocalBlobStorage:
    #     storage = request.param("unit-tests", MyMetadata, content_type="text/plain", root_path=tmp_path)
    # else:
    #     if request.param == GcpBlobStorage:
    #         bucket_name = os.environ.get("GOOGLE_DEFAULT_BUCKET_NAME")
    #         if not bucket_name:
    #             raise ValueError("GOOGLE_DEFAULT_BUCKET_NAME is not set")
    #         GcpBlobStorage.init_client(bucket_name)
    storage = request.param("unit-tests-001", collection_name="test_all_async_blob_storage", clazz=MyMetadata, content_type="text/plain")
    yield storage
    storage.drop()


@pytest.mark.asyncio
async def test_upload_blob(storage: BaseAsyncBlobStorage):
    # Given: A file name with content
    file_name = "test/file"
    data = b"test data"
    blob = Blob(name=file_name, data=data)
    # When: I upload it
    await storage.upload_async(blob)
    # Then: It is uploaded
    assert file_name in list([b.name for b in storage.list_blobs()])


@pytest.mark.asyncio
async def test_upload_blob_with_metadata(storage: BaseAsyncBlobStorage):
    file_name = "test/file"
    data = b"test data"
    metadata = MyMetadata(name="test", age=10)
    blob = Blob(name=file_name, data=data, metadata=metadata)
    # When: Upload blob with metadata
    await storage.upload_async(blob)
    # Then: Metadata is saved
    assert metadata == storage.get_metadata(file_name)

@pytest.mark.skip
def test_upload_file_with_metadata(storage: BaseBlobStorage, tmp_path: Path):
    # Given: File
    file_path = tmp_path.joinpath("test.txt")
    with open(file_path, "wb") as f:
        f.write(b"test data")
    metadata = MyMetadata(name="test", age=10)
    # When: Upload blob with metadata
    storage.upload_file(file_path, metadata)
    # Then: Metadata is saved
    assert metadata == storage.get_metadata("test")

@pytest.mark.asyncio
async def test_download_blob(storage: BaseAsyncBlobStorage):
    # Given: A file name with content 
    blob = Blob(name="file.txt", data="test data")
    # And: It is stored
    await storage.upload_async(blob)
    # When: I download it
    downloaded_blob = await storage.download_async(blob.name)
    # Then: It is downloaded
    assert downloaded_blob.name == blob.name
    assert downloaded_blob.data.read() == blob.data.read()

@pytest.mark.asyncio
async def test_download_nonexistent_blob(storage: BaseAsyncBlobStorage):
    # Given: A not existing file name
    file_name = "file_not_exists.txt"
    # When: It is downloaded
    # Then: An exception is raised
    with pytest.raises(KeyNotExistsException):
        await storage.download_async(file_name)

@pytest.mark.asyncio
async def test_get_metadata(storage: BaseAsyncBlobStorage):
    # Given: A blob with metadata
    blob = Blob(name="file.txt", data="test data", metadata=MyMetadata(name="test", age=10))
    # And: It is stored
    await storage.upload_async(blob)
    # When: A metadata is gotten
    retrieved_metadata = storage.get_metadata(blob.name)
    # Then: It is received
    assert retrieved_metadata == blob.metadata


def test_get_nonexistent_metadata(storage: BaseAsyncBlobStorage):
    # Given: A not existing file name
    file_name = "file_not_exists.txt"
    # When: Get a metadata
    # Then: An exception is raised
    with pytest.raises(KeyNotExistsException):
        storage.get_metadata(file_name)


# def test_upload_blob_with_default_ext(tmp_path: Path):
#     storage = LocalBlobStorage(
#         str(tmp_path.joinpath("test_bucket")),
#         content_type="text/plain",
#         subfolder_characters=2,
#     )
#     file_name = "test/file"
#     data = b"test data"
#     storage.upload_blob(file_name, data)
#     exp_path = tmp_path.joinpath("test_bucket", "test", "fi", "file.txt")
#     assert exp_path.exists()
#     with open(exp_path, "rb") as f:
#         assert f.read() == data

@pytest.mark.asyncio
async def test_names(storage: BaseAsyncBlobStorage):
    # Given: A blob with content
    blob = Blob(name="file.txt", data="test data")
    # And: It is stored
    await storage.upload_async(blob)
    # When: Get names
    names = list(storage.names())
    assert len(names) == 1
    assert blob.name in list(names)

@pytest.mark.asyncio
async def test_delete(storage: BaseAsyncBlobStorage):
    # Give: An uploaded file
    blob = Blob(name="file.txt", data="test data")
    await storage.upload_async(blob)
    assert blob.name in list(storage.names())
    # When: I delete the file
    storage.delete(blob.name)
    # Then: The file is deleted
    assert blob.name not in list(storage.names())

@pytest.mark.asyncio
async def test_exists(storage: BaseAsyncBlobStorage):
    # Give: An uploaded file
    blob = Blob(name="file.txt", data="test data")
    await storage.upload_async(blob)
    # Then: It exists
    assert storage.exists(blob.name)
    # When: Delete the file
    storage.delete(blob.name)
    # Then: It not exists
    assert not storage.exists(blob.name)

@pytest.mark.asyncio
async def test_list_blobs(storage: BaseAsyncBlobStorage):
    # Give: An uploaded blob
    blob = Blob(name="test/file.txt", data="test data")
    await storage.upload_async(blob)
    # When: List blobs
    blobs = list(storage.list_blobs("test"))
    # Then: The file is listed
    assert len(blobs) == 1
    assert blobs[0].name == "test/file.txt"
    assert blobs[0].content_type == "text/plain"

@pytest.mark.asyncio
async def test_delete_folder(storage: BaseAsyncBlobStorage):
    # Give: An uploaded blob in test1 folder
    blob1 = Blob(name="test1/file.txt", data="test data")
    await storage.upload_async(blob1)
    assert blob1.name in list(storage.names("test1"))
    # And: An uploaded blob in test2 folder
    blob2 = Blob(name="test2/file.txt", data="test data")
    await storage.upload_async(blob2)
    assert blob2.name in list(storage.names("test2"))
    # When: I delete the folder test1
    storage.delete_folder("test1")
    # Then: The file 1 is deleted
    assert blob1.name not in list(storage.names())
    # And: The file 2 exists
    assert blob2.name in list(storage.names())

@pytest.mark.skip
def test_move_blob(storage: BaseBlobStorage):
    source_key = "test/source"
    dest_key = "test/dest"
    data = b"test data"
    storage.upload_blob(source_key, data)
    storage.move_blob(source_key, dest_key)
    assert dest_key in list(storage.keys())
    assert source_key not in list(storage.keys())
    assert data == storage.download_blob(dest_key)
