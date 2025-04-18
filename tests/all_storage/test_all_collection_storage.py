import pytest
from pydantic import BaseModel

from ampf.base import (
    BaseStorage,
    CollectionDef,
)
from ampf.gcp.gcp_factory import GcpFactory
from ampf.in_memory.in_memory_factory import InMemoryFactory
from ampf.local.local_factory import LocalFactory


class D(BaseModel):
    name: str
    value: str


class C(BaseModel):
    id: str
    value: str


@pytest.fixture
def collection_def():
    return CollectionDef("test", D, subcollections=[CollectionDef("children", C)])


@pytest.fixture(params=[InMemoryFactory, LocalFactory, GcpFactory])
def storage(gcp_factory, request, tmp_path, collection_def):
    if request.param == LocalFactory:
        factory = request.param(tmp_path)
    elif request.param == GcpFactory:
        factory = gcp_factory
    else:
        factory = request.param()
    storage = factory.create_collection(collection_def)
    yield storage
    storage.drop()


def test_create_new(storage: BaseStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I create it
    storage.create(d)
    # Then: Is created
    assert ["foo"] == list(storage.keys())
