from pydantic import BaseModel
import pytest

from ampf.base import BaseStorage, KeyNotExistsException
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
