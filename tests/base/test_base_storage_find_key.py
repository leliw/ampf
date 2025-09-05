from uuid import UUID

from pydantic import BaseModel
import pytest

from ampf.in_memory import InMemoryStorage, InMemoryAsyncStorage

@pytest.fixture(params=[InMemoryStorage, InMemoryAsyncStorage])
def StorageClass(request):
    return request.param



def test_key_id(StorageClass):
    # Given: A class with id field
    class D(BaseModel):
        name: str
        value: str
        id: int

    # When: A storage is created
    storage = StorageClass("test", D)
    # Then: The key is "id"
    assert storage.key == "id"


def test_key_uuid(StorageClass):
    # Given: A class with id field
    class D(BaseModel):
        name: str
        value: str
        uuid: UUID

    # When: A storage is created
    storage = StorageClass("test", D)
    # Then: The key is "uuid"
    assert storage.key == "uuid"


def test_key_uid(StorageClass):
    # Given: A class with id field
    class D(BaseModel):
        name: str
        value: str
        uid: UUID

    # When: A storage is created
    storage = StorageClass("test", D)
    # Then: The key is "uid"
    assert storage.key == "uid"


def test_key_first_field(StorageClass):
    # Given: A class with id field
    class D(BaseModel):
        name: str
        value: str

    # When: A storage is created
    storage = StorageClass("test", D)
    # Then: The key is "name"
    assert storage.key == "name"
