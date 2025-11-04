import pytest
from pydantic import BaseModel

from ampf.base.exceptions import KeyNotExistsException
from ampf.local.json_multi_files_storage import JsonMultiFilesStorage


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def storage(tmp_path):
    return JsonMultiFilesStorage[D](
        collection_name="test",
        clazz=D,
        key_name="name",
        subfolder_characters=2,
        root_path=tmp_path,
    )


def test_simple_key_all(storage):
    d = D(name="foo", value="beer")
    storage.put("foo", d)

    assert ["foo"] == list(storage.keys())
    assert d == storage.get("foo")

    storage.delete("foo")
    assert [] == list(storage.keys())
    with pytest.raises(KeyNotExistsException):
        storage.get("foo")


def test_folder_key_all(storage):
    d = D(name="kung/foo", value="beer")
    storage.put("kung/foo", d)

    assert ["kung/foo"] == list(storage.keys())
    assert d == storage.get("kung/foo")

    storage.delete("kung/foo")
    assert [] == list(storage.keys())
    with pytest.raises(KeyNotExistsException):
        storage.get("kung/foo")
