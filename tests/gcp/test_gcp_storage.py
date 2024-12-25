from pydantic import BaseModel
import pytest

from ampf.gcp import GcpStorage


class TC(BaseModel):
    name: str


@pytest.fixture
def storage():
    return GcpStorage("unit tests", TC)


def test_storage(storage: GcpStorage[TC]):
    storage.put("1", TC(name="test"))

    assert storage.get("1") == TC(name="test")
    assert list(storage.keys()) == ["1"]
    assert list(storage.get_all()) == [TC(name="test")]

    storage.delete("1")

    assert list(storage.keys()) == []

    storage.put("2", TC(name="test2"))
    storage.put("3", TC(name="test3"))
    storage.drop()

    assert list(storage.keys()) == []
