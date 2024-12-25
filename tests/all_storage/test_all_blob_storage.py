import pytest
from pydantic import BaseModel, Field

from ampf.base import BaseBlobStorage, KeyNotExistsException
from ampf.in_memory import InMemoryBlobStorage
from ampf.local import FileStorage, LocalBlobStorage


class MyMetadata(BaseModel):
    name: str = Field(...)
    age: int = Field(...)


@pytest.fixture(params=[InMemoryBlobStorage, LocalBlobStorage])
def storage(request, tmp_path):
    if request.param in [LocalBlobStorage]:
        FileStorage._root_dir_path = tmp_path
    storage = request.param("test_bucket", MyMetadata)
    yield storage
    storage.drop()


def test_upload_blob(storage: BaseBlobStorage):
    # Given: A file name with content
    file_name = "test/file.txt"
    data = b"test data"
    # When: I upload it
    storage.upload_blob(file_name, data)
    # Then: It is uploaded
    assert file_name in list(storage.keys())


def test_upload_blob_with_metadata(storage):
    file_name = "test/file.txt"
    data = b"test data"
    metadata = MyMetadata(name="test", age=10)
    # When: Upload blob with metadata
    storage.upload_blob(file_name, data, metadata)
    # Then: Metadata is saved
    assert metadata == storage.get_metadata(file_name)


def test_download_blob(storage):
    file_name = "test/file.txt"
    data = b"test data"
    storage.upload_blob(file_name, data)
    downloaded_data = storage.download_blob(file_name)
    assert downloaded_data == data


def test_download_nonexistent_blob(storage: BaseBlobStorage):
    # Given: A not existing file name
    file_name = "test/file.txt"
    # When: It is downloaded
    # Then: An exception is raised
    with pytest.raises(KeyNotExistsException):
        storage.download_blob(file_name)


def test_get_metadata(storage):
    file_name = "test/file.txt"
    metadata = MyMetadata(name="test", age=10)
    storage.upload_blob(file_name, b"test data", metadata)
    retrieved_metadata = storage.get_metadata(file_name)
    assert retrieved_metadata == metadata


def test_get_nonexistent_metadata(storage):
    file_name = "test/file.txt"
    with pytest.raises(KeyNotExistsException):
        storage.get_metadata(file_name)


def test_upload_blob_with_default_ext(tmp_path):
    storage = LocalBlobStorage(
        str(tmp_path.joinpath("test_bucket")), default_ext="txt", subfolder_characters=2
    )
    file_name = "test/file"
    data = b"test data"
    storage.upload_blob(file_name, data)
    exp_path = tmp_path.joinpath("test_bucket", "test", "fi", "file.txt")
    assert exp_path.exists()
    with open(exp_path, "rb") as f:
        assert f.read() == data


def test_keys(storage: BaseBlobStorage):
    file_name = "test/file.txt"
    storage.upload_blob(file_name, b"test data")
    assert file_name in list(storage.keys())


def test_delete(storage: BaseBlobStorage):
    # Give: An uploaded file
    file_name = "test/file.txt"
    storage.upload_blob(file_name, b"test data")
    assert file_name in list(storage.keys())
    # When: I delete the file
    storage.delete(file_name)
    # Then: The file is deleted
    assert file_name not in list(storage.keys())

def test_list_blobs(storage: BaseBlobStorage):
    # Give: An uploaded file
    file_name = "test/file.txt"
    storage.upload_blob(file_name, b"test data", content_type="text/plain")
    # When: I list blobs 
    blobs = list(storage.list_blobs("test"))
    # Then: The file is listed
    assert len(blobs) == 1
    assert blobs[0].name == "file.txt"
    assert blobs[0].mime_type == "text/plain"

def test_delete_folder(storage: BaseBlobStorage):
    # Give: An uploaded file
    file_name = "test/file.txt"
    storage.upload_blob(file_name, b"test data")
    assert file_name in list(storage.keys())
    # When: I delete the folder
    storage.delete_folder("test")
    # Then: The file is deleted
    assert file_name not in list(storage.keys())
