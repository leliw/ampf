from uuid import UUID, uuid4
from pydantic import BaseModel, Field
import pytest

from ampf.base import BaseStorage, KeyExistsException, KeyNotExistsException
from ampf.base.base_query_storage import BaseQueryStorage
from ampf.gcp import GcpStorage
from ampf.in_memory import InMemoryStorage
from ampf.local import JsonOneFileStorage, JsonMultiFilesStorage


class D(BaseModel):
    name: str
    value: str


class Duuid(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    name: str
    value: str


@pytest.fixture(params=[InMemoryStorage, JsonOneFileStorage, JsonMultiFilesStorage, GcpStorage])
def storage(gcp_factory, request, tmp_path):
    if request.param in [JsonOneFileStorage, JsonMultiFilesStorage]:
        storage = request.param("test", D, root_path=tmp_path)
    elif request.param == GcpStorage:
        storage = gcp_factory.create_storage("test", D)
    else:
        storage = request.param("test", D)
    yield storage
    storage.drop()


@pytest.fixture(params=[InMemoryStorage, JsonOneFileStorage, JsonMultiFilesStorage, GcpStorage])
def storage_key(gcp_factory, request, tmp_path):
    if request.param in [JsonOneFileStorage, JsonMultiFilesStorage]:
        storage = request.param("test", D, key=lambda d: d.value, root_path=tmp_path)
    elif request.param == GcpStorage:
        storage = gcp_factory.create_storage("test", D, key=lambda d: d.value)
    else:
        storage = request.param("test", D, key=lambda d: d.value)
    yield storage
    storage.drop()


@pytest.fixture(params=[InMemoryStorage, JsonOneFileStorage, JsonMultiFilesStorage, GcpStorage])
def storage_uuid(gcp_factory, request, tmp_path):
    if request.param in [JsonOneFileStorage, JsonMultiFilesStorage]:
        storage = request.param("test", Duuid, root_path=tmp_path)
    elif request.param == GcpStorage:
        storage = gcp_factory.create_storage("test", Duuid)
    else:
        storage = request.param("test", Duuid)
    yield storage
    storage.drop()


def test_not_found(storage: BaseStorage):
    # When: I get something from empty storage
    # Then: Is exception rised
    with pytest.raises(KeyNotExistsException):
        storage.get("foo")


def test_create_new(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I create it
    storage.create(d)
    # Then: Is created
    assert ["foo"] == list(storage.keys())


def test_create_already_exists(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # And: It is already created
    storage.create(d)
    # When:
    # I try to create it again
    with pytest.raises(KeyExistsException):
        storage.create(d)


def test_save_not_exists(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I save it
    storage.save(d)
    # Then: Is saved
    assert ["foo"] == list(storage.keys())


def test_save_exists(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # And: It is already saved
    storage.save(d)
    # When: I save it again
    storage.save(d)
    # Then: Is saved
    assert ["foo"] == list(storage.keys())


def test_get_key_name(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I get the key
    key = storage.get_key(d)
    # Then: The key is correct
    assert "foo" == key


def test_get_key(storage_key: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I get the key
    key = storage_key.get_key(d)
    # Then: The key is correct
    assert "beer" == key


def test_get_all(storage: BaseStorage):
    # Given: Some elements
    d1 = D(name="foo", value="beer")
    d2 = D(name="bar", value="wine")
    storage.save(d1)
    storage.save(d2)
    # When: I get all elements
    all_elements = list(storage.get_all())
    # Then: All elements are returned
    assert d1 in all_elements
    assert d2 in all_elements
    assert len(all_elements) == 2


def test_key_exists(storage: BaseStorage):
    # Given: Some elements
    d1 = D(name="foo", value="beer")
    d2 = D(name="bar", value="wine")
    storage.save(d1)
    storage.save(d2)
    # When: I check if key exists
    assert storage.key_exists("foo")
    assert not storage.key_exists("baz")


def test_is_empty(storage: BaseStorage):
    # Given: An empty storage
    assert storage.is_empty()
    # When: I add an element
    d = D(name="foo", value="beer")
    storage.save(d)
    # Then: Is not empty
    assert not storage.is_empty()


def test_delete_existing(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # And: It is created
    storage.create(d)
    # When: I delete it
    storage.delete("foo")
    # Then: It is not exist
    assert not storage.key_exists("foo")


def test_uuid(storage_uuid: BaseStorage):
    d = Duuid(name="foo", value="beer")
    storage_uuid.create(d)
    o = storage_uuid.get(d.uuid)
    assert d == o
    o.value = "wine"
    storage_uuid.put(o.uuid, o)
    assert o == storage_uuid.get(o.uuid)
    storage_uuid.delete(d.uuid)
    assert not storage_uuid.key_exists(d.uuid)

def test_query(storage: BaseQueryStorage):
    # Given: Stored two elements with the same value and one with other
    storage.save(D(name="foo", value="beer"))
    storage.save(D(name="bar", value="beer"))
    storage.save(D(name="baz", value="wine"))
    # When: Get all items with "beer"
    ret = list(storage.where("value", "==", "beer").get_all())
    # Then: Two items are returned
    assert len(ret) == 2
    assert ret[0].name in ["foo", "bar"]
    assert ret[1].name in ["foo", "bar"]
    # When: Get all items different than "beer"
    ret = list(storage.where("value", "!=", "beer").get_all())
    # Then: One item is returned
    assert len(ret) == 1
    assert ret[0].name == "baz"

def test_query_uuid(storage_uuid: BaseQueryStorage):
    # Given: A stred element with UUID filed
    d = Duuid(name="foo", value="beer")
    storage_uuid.create(d)
    # When: Filrter by UUID
    ret = [item for item in storage_uuid.where("uuid", "==", d.uuid).get_all()]
    # Then: The element is returned
    assert len(ret) == 1
