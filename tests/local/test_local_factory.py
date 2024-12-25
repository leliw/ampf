from pydantic import BaseModel
import pytest

from ampf.local import LocalFactory


@pytest.fixture
def factory(tmp_path):
    return LocalFactory(tmp_path)


class T(BaseModel):
    name: str


def test_create_storage(factory):
    storage = factory.create_storage("test", T, "name")

    assert storage is not None


def test_create_compact_storage(factory):
    storage = factory.create_compact_storage("test", T, "name")

    assert storage is not None
