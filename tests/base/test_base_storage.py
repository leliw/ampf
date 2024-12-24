from pydantic import BaseModel
import pytest

from ampf.base import BaseStorage, KeyExistsException
from ampf.in_memory import InMemoryStorage


class D(BaseModel):
    name: str
    value: str

@pytest.fixture
def storage():
    return InMemoryStorage("test", D)


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

def test_get_key(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I get the key
    key = storage.get_key(d)
    # Then: The key is correct
    assert "foo" == key

def test_get_all(storage: BaseStorage):
    # Given: Some elements
    d1 = D(name="foo", value="beer")
    d2 = D(name="bar", value="wine")
    storage.save(d1)
    storage.save(d2)
    # When: I get all elements
    all_elements = list(storage.get_all())
    # Then: All elements are returned
    assert [d1, d2] == all_elements

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

