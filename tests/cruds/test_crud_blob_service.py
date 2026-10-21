import pytest

from ampf.base import BaseBlobMetadata, Blob
from ampf.base.exceptions import KeyNotExistsException
from ampf.cruds.crud_blob_service import CRUDBlobService
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory


class TMetadata(BaseBlobMetadata):
    pass


@pytest.fixture
def service() -> CRUDBlobService[TMetadata]:
    storage = InMemoryAsyncFactory().create_blob_storage("test", TMetadata)
    return CRUDBlobService(storage, TMetadata)


async def test_get_headers(service: CRUDBlobService):
    result = [header async for header in service.get_headers()]
    assert len(result) == 0


async def test_upload_and_download(service: CRUDBlobService):
    metadata = TMetadata(content_type="text/plain")
    blob = Blob("X", content="X", metadata=metadata)
    await service.upload(blob)
    result = [header async for header in service.get_headers()]
    assert len(result) == 1

    result = await service.download(blob.name)
    assert result.content == blob.content


def test_create_blob_location(service: CRUDBlobService):
    result = service.create_blob_location("example.txt")
    assert result.bucket == "__default__"
    assert result.name == "test/example.txt"


async def test_get_metadata(service: CRUDBlobService):
    metadata = TMetadata(content_type="text/plain")
    blob = Blob("X", content="X", metadata=metadata)
    await service.upload(blob)
    result = await service.get_metadata(blob.name)
    assert result == metadata


async def test_put_metadata(service: CRUDBlobService[TMetadata]):
    metadata = TMetadata(content_type="text/plain")
    blob = Blob("X", content="X", metadata=metadata)
    await service.upload(blob)
    result = await service.get_metadata(blob.name)
    assert result == metadata
    metadata = TMetadata(content_type="text/markdown")
    await service.put_metadata(blob.name, metadata)
    result = await service.get_metadata(blob.name)
    assert result.content_type == metadata.content_type


async def test_delete(service: CRUDBlobService):
    metadata = TMetadata(content_type="text/plain")
    blob = Blob("X", content="X", metadata=metadata)
    await service.upload(blob)
    result = await service.get_metadata(blob.name)
    assert result == metadata
    await service.delete(blob.name)
    with pytest.raises(KeyNotExistsException):
        await service.download(blob.name)
