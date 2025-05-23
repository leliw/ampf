from pydantic import BaseModel
import pytest

from ampf.gcp import GcpFactory
from ampf.in_memory import InMemoryFactory
from ampf.local import LocalFactory


@pytest.fixture(params=[InMemoryFactory, LocalFactory, GcpFactory])
def factory(gcp_factory, request, tmp_path):
    if request.param == LocalFactory:
        factory = request.param(tmp_path)
    elif request.param == GcpFactory:
        factory = gcp_factory
    else:
        factory = request.param()
    return factory


class T(BaseModel):
    name: str


def test_create_storage(factory):
    storage = factory.create_storage("test", T, "name")

    assert storage is not None


def test_create_compact_storage(factory):
    storage = factory.create_compact_storage("test", T, "name")

    assert storage is not None

def test_create_blob_storage(factory):
    storage = factory.create_blob_storage("test", T, )

    assert storage is not None