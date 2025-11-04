from typing import List, Optional

import pytest
from pydantic import BaseModel

from ampf.base import BaseStorage, KeyExistsException
from ampf.base.exceptions import KeyNotExistsException
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


def test_patch_not_exists(storage: BaseStorage):
    # Given: A patch data
    patch_data = {"value": "wine"}
    # When: I patch not existing object
    with pytest.raises(KeyNotExistsException):
        storage.patch("foo", patch_data)


def test_patch_with_dict(storage: BaseStorage):
    # Given: A patch data
    patch_data = {"value": "wine"}
    # And: A stored object
    storage.create(D(name="foo", value="beer"))
    # When: I patch not existing object
    storage.patch("foo", patch_data)
    # Then: Is patched
    assert D(name="foo", value="wine") == storage.get("foo")


def test_patch_with_pydantic(storage: BaseStorage):
    # Given: A patch data
    class DPatch(BaseModel):
        name: Optional[str] = None
        value: Optional[str] = None

    patch_data = DPatch(value="wine")
    # And: A stored object
    storage.create(D(name="foo", value="beer"))
    # When: I patch existing object
    storage.patch("foo", patch_data)
    # Then: Is patched
    assert D(name="foo", value="wine") == storage.get("foo")


def test_patch_key_value(storage: BaseStorage):
    # Given: A stored object
    storage.create(D(name="foo", value="beer"))
    # When: I patch with new key
    storage.patch("foo", {"name": "bar"})
    # Then: An old key doesn't exist
    with pytest.raises(KeyNotExistsException):
        storage.get("foo")
    # And: A new key exists
    assert D(name="bar", value="beer") == storage.get("bar")


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


def test_count(storage: BaseStorage):
    # Given: A storage with an element
    storage.create(D(name="foo", value="beer"))
    # When: Count elements
    ret = storage.count()
    # Then: Count is 1
    assert ret == 1


def test_get_key_not_set():
    # Given: A storage without key set
    storage = InMemoryStorage("test", D)
    # And: A new element
    d = D(name="foo", value="beer")
    # When: I get the key
    key = storage.get_key(d)
    # Then: The first attribute is returned
    assert "foo" == key


def test_get_key_name_is_set():
    # Given: A storage with key name
    storage = InMemoryStorage("test", D, key_name="value")
    # And: A new element
    d = D(name="foo", value="beer")
    # When: I get the key
    key = storage.get_key(d)
    # Then: The attribute key name is returned
    assert "beer" == key


def test_get_key_as_lambda():
    # Given: A storage with key name
    storage = InMemoryStorage("test", D, key=lambda d: f"{d.name}/{d.value}")
    # And: A new element
    d = D(name="foo", value="beer")
    # When: I get the key
    key = storage.get_key(d)
    # Then: The attribute key name is returned
    assert "foo/beer" == key


def test_create_collection(storage: BaseStorage):
    # When: Collection is created
    ret = storage.create_collection("foo", "subcoll", D)
    # Then: Collection is returned
    assert issubclass(ret.__class__, BaseStorage)
    # And: Value can be saved and read
    ret.save(D(name="foo", value="bar"))
    assert D(name="foo", value="bar") == ret.get("foo")
    # And: Parent storage is unchanged
    assert ["foo"] not in list(storage.keys())


class TC(BaseModel):
    name: str
    embedding: Optional[List[float]] = None


def test_embedding(storage: BaseStorage[TC]):
    # Given: Data with embedding
    tc1 = TC(name="test1", embedding=[1.0, 2.0, 3.0])
    tc2 = TC(name="test2", embedding=[4.0, 5.0, 6.0])
    # When: Save them
    storage.put("1", tc1)
    storage.put("2", tc2)
    # And: Find nearest
    nearest = list(storage.find_nearest(tc1.embedding or []))
    # Then: All two are returned
    assert len(nearest) == 2
    # And: The nearest is the first one
    assert nearest[0] == tc1
    # And: The second is the second
    assert nearest[1] == tc2


if __name__ == "__main__":
    pytest.main([__file__])
