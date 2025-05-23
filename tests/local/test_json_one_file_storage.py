from pydantic import BaseModel
import pytest
from ampf.base import KeyExistsException, KeyNotExistsException
from ampf.local.file_storage import FileStorage
from ampf.local.json_one_file_storage import JsonOneFileStorage


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def t(tmp_path):
    return JsonOneFileStorage[D]("data", D, root_path=tmp_path)


def test_constructor(tmp_path):
    # Basic usage - file_name as string
    t = JsonOneFileStorage[D](collection_name="data", clazz=D, key_name="name", root_path=tmp_path)
    assert t.file_path == tmp_path.joinpath("data.json")
    # Basic usage - subcollections
    t = JsonOneFileStorage[D]("users/user_id/preferences", D, key_name="name", root_path=tmp_path)
    assert t.file_path == tmp_path.joinpath("users/user_id/preferences.json")
    # test file name - string with ext
    t3 = JsonOneFileStorage[D]("data.json", D, key_name="name", root_path=tmp_path)
    assert t3.file_path == tmp_path.joinpath("data.json")
    # test file name - string without ext
    t4 = JsonOneFileStorage[D]("data", D, key_name="name", root_path=tmp_path)
    assert t4.file_path == tmp_path.joinpath("data.json")


def test_simple_key_all(t):
    d = D(name="foo", value="beer")
    t.put("foo", d)

    assert ["foo"] == list(t.keys())
    assert d == t.get("foo")

    t.delete("foo")
    assert [] == list(t.keys())
    with pytest.raises(KeyNotExistsException):
        t.get("foo")


def test_folder_key_all(t):
    d = D(name="kung/foo", value="beer")
    t.put("kung/foo", d)

    assert ["kung/foo"] == list(t.keys())
    assert d == t.get("kung/foo")

    t.delete("kung/foo")
    with pytest.raises(KeyNotExistsException):
        t.get("kung/foo")


def test_is_empty(t):
    assert t.is_empty()


def test_create(t):
    d = D(name="foo", value="beer")
    t.create(d)
    assert ["foo"] == list(t.keys())
    with pytest.raises(KeyExistsException):
        t.create(d)


def test_drop(t):
    d = D(name="foo", value="beer")
    t.create(d)

    t.drop()

    assert t.is_empty()


def test_key_isnt_stored_in_value(t):
    t.save(D(name="1", value="a"))
    d = t._load_data()

    assert "1" in d.keys()
    assert "name" not in d["1"].keys()
