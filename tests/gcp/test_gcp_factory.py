from pydantic import BaseModel
import pytest

from ampf.gcp import GcpFactory


@pytest.fixture
def factory():
    GcpFactory.init_client()
    return GcpFactory()


class T(BaseModel):
    name: str


def test_create_storage(factory: GcpFactory):
    storage = factory.create_storage("test", T, "name")

    assert storage is not None


def test_create_compact_storage(factory):
    storage = factory.create_compact_storage("test", T, "name")

    assert storage is not None
