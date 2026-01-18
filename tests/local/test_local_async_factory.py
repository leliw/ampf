from pathlib import Path
from pydantic import BaseModel
import pytest

from ampf.base.blob_model import Blob, BlobLocation
from ampf.local import LocalAsyncFactory


@pytest.fixture
def factory(tmp_path):
    return LocalAsyncFactory(tmp_path)


class T(BaseModel):
    name: str


def test_create_storage(factory):
    storage = factory.create_storage("test", T, "name")

    assert storage is not None


def test_create_compact_storage(factory):
    storage = factory.create_compact_storage("test", T, "name")

    assert storage is not None


@pytest.mark.asyncio
async def test_upload_and_download_blob(factory: LocalAsyncFactory, tmp_path: Path):
    # Given: A blob and a blob location
    blob_location = BlobLocation(name="blob_test.txt", bucket= str(tmp_path / "test"))
    blob = Blob(name="blob_test.txt", content=b"test data")
    # When: A blob is uploaded
    await factory.upload_blob(blob_location, blob)
    # Then: It can be downloaded
    blob = await factory.download_blob(blob_location)
    assert blob.content == b"test data"
    # And: The blob file exists in the expected location
    blob_file_path = tmp_path / "test" / "blobs" / "blob_test.txt"
    assert blob_file_path.exists()