import pytest
from pydantic import BaseModel

from ampf.base import BaseQueryStorage, BaseStorage, KeyNotExistsException
from ampf.in_memory import InMemoryStorage


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def storage():
    return InMemoryStorage("test", D)


def test_storage_all(storage: BaseStorage):
    assert storage.is_empty()

    d = D(name="foo", value="beer")
    storage.put("foo", d)

    assert ["foo"] == list(storage.keys())
    assert d == storage.get("foo")

    assert not storage.is_empty()

    storage.delete("foo")
    assert [] == list(storage.keys())
    with pytest.raises(KeyNotExistsException):
        storage.get("foo")

    storage.put(d.name, d)
    storage.drop()
    assert [] == list(storage.keys())


def test_query(storage: BaseQueryStorage):
    # Given: Stored two elements with the same value and one with other
    storage.save(D(name="foo", value="beer"))
    storage.save(D(name="bar", value="beer"))
    storage.save(D(name="baz", value="wine"))
    # When: Get all items with "beer"
    ret = list(storage.where("value", "==", "beer").get_all())
    # Then: Two items are returned
    assert len(ret) == 2
    assert ret[0].name == "foo"
    assert ret[1].name == "bar"
