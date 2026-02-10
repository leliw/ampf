import os
from pathlib import Path

import pytest
from pydantic import Field

from ampf.base import BaseBlobMetadata, BaseBlobStorage, KeyNotExistsException
from ampf.base.blob_model import Blob
from ampf.gcp import GcpBlobStorage
from ampf.in_memory import InMemoryBlobStorage
from ampf.local import LocalBlobStorage


class MyMetadata(BaseBlobMetadata):
    name: str = Field(...)
    age: int = Field(...)


@pytest.fixture(params=[InMemoryBlobStorage, LocalBlobStorage, GcpBlobStorage])
def storage(gcp_factory, request, tmp_path):
    if request.param == LocalBlobStorage:
        storage = request.param("unit-tests", MyMetadata, content_type="text/plain", root_path=tmp_path)
    else:
        if request.param == GcpBlobStorage:
            bucket_name = os.environ.get("GOOGLE_DEFAULT_BUCKET_NAME")
            if not bucket_name:
                raise ValueError("GOOGLE_DEFAULT_BUCKET_NAME is not set")
            GcpBlobStorage.init_client(bucket_name)
        storage = request.param("unit-tests", MyMetadata, content_type="text/plain")
    yield storage
    storage.drop()


def test_upload_blob(storage: BaseBlobStorage):
    # Given: A file name with content
    file_name = "test/file"
    data = b"test data"
    # When: I upload it
    storage.upload_blob(file_name, data)
    # Then: It is uploaded
    assert file_name in list(storage.keys())


def test_upload_blob_with_metadata(storage: BaseBlobStorage):
    file_name = "test/file"
    data = b"test data"
    metadata = MyMetadata(name="test", age=10)
    # When: Upload blob with metadata
    storage.upload_blob(file_name, data, metadata)
    # Then: Metadata is saved
    assert metadata == storage.get_metadata(file_name)


def test_upload_file_with_metadata(storage: BaseBlobStorage, tmp_path: Path):
    # Given: File
    file_path = tmp_path.joinpath("test.txt")
    with open(file_path, "wb") as f:
        f.write(b"test data")
    metadata = MyMetadata(name="test", age=10)
    # When: Upload blob with metadata
    storage.upload_file(file_path, metadata=metadata)
    # Then: Metadata is saved
    assert metadata == storage.get_metadata("test")


def test_download_blob(storage: BaseBlobStorage):
    file_name = "test/file"
    data = b"test data"
    storage.upload_blob(file_name, data)
    downloaded_data = storage.download_blob(file_name)
    assert downloaded_data == data


def test_download_nonexistent_blob(storage: BaseBlobStorage):
    # Given: A not existing file name
    file_name = "test/file"
    # When: It is downloaded
    # Then: An exception is raised
    with pytest.raises(KeyNotExistsException):
        storage.download_blob(file_name)


def test_get_metadata(storage: BaseBlobStorage):
    file_name = "test/file"
    metadata = MyMetadata(name="test", age=10)
    storage.upload_blob(file_name, b"test data", metadata)
    retrieved_metadata = storage.get_metadata(file_name)
    assert retrieved_metadata == metadata


def test_get_nonexistent_metadata(storage: BaseBlobStorage):
    file_name = "test/file"
    with pytest.raises(KeyNotExistsException):
        storage.get_metadata(file_name)


def test_upload_blob_with_default_ext(tmp_path: Path):
    storage = LocalBlobStorage(
        str(tmp_path.joinpath("test_bucket")),
        content_type="text/plain",
        subfolder_characters=2,
    )
    file_name = "test/file"
    data = b"test data"
    storage.upload_blob(file_name, data)
    exp_path = tmp_path.joinpath("test_bucket", "test", "fi", "file.txt")
    assert exp_path.exists()
    with open(exp_path, "rb") as f:
        assert f.read() == data


def test_keys(storage: BaseBlobStorage):
    file_name = "test/file"
    metadata = MyMetadata(name="test", age=10)
    storage.upload_blob(file_name, b"test data", metadata)
    keys = list(storage.keys())
    assert len(keys) == 1
    assert file_name in list(keys)


def test_delete(storage: BaseBlobStorage):
    # Give: An uploaded file
    file_name = "test/file"
    storage.upload_blob(file_name, b"test data")
    assert file_name in list(storage.keys())
    # When: I delete the file
    storage.delete(file_name)
    # Then: The file is deleted
    assert file_name not in list(storage.keys())


def test_delete_not_existing(storage: BaseBlobStorage):
    # When: I delete the file
    with pytest.raises(KeyNotExistsException) as e:
        storage.delete("not_existing")
    # Then: The file is deleted
    assert e.value.key == "not_existing"


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
    file_name = "test/file"
    storage.upload_blob(file_name, b"test data")
    assert file_name in list(storage.keys())
    # When: I delete the folder
    storage.delete_folder("test")
    # Then: The file is deleted
    assert file_name not in list(storage.keys())


def test_move_blob(storage: BaseBlobStorage):
    source_key = "test/source"
    dest_key = "test/dest"
    data = b"test data"
    storage.upload_blob(source_key, data)
    storage.move_blob(source_key, dest_key)
    assert dest_key in list(storage.keys())
    assert source_key not in list(storage.keys())
    assert data == storage.download_blob(dest_key)


blob = Blob(
    name="test/file",
    content=b"test data",
    metadata=MyMetadata(name="test", age=10, content_type="text/plain"),
)


def test_upload(storage: BaseBlobStorage):
    # Given: A blob
    assert blob
    # When: I upload it
    storage.upload(blob)
    # Then: It is uploaded
    assert blob.name in list(storage.keys())


def test_download(storage: BaseBlobStorage):
    # Given: An uploaded blob
    storage.upload(blob)
    # When: I download it
    downloaded_blob = storage.download(blob.name)
    # Then: A downloaded blob is the same as the original
    assert downloaded_blob.name == blob.name
    assert downloaded_blob.content == blob.content
    assert downloaded_blob.metadata == blob.metadata
