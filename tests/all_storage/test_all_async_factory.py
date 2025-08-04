from pydantic import BaseModel
import pytest

from ampf.gcp import GcpAsyncFactory
from ampf.in_memory import InMemoryAsyncFactory
from ampf.local_async import AsyncLocalFactory


@pytest.fixture(params=[InMemoryAsyncFactory, AsyncLocalFactory, GcpAsyncFactory])
def factory(gcp_factory, request, tmp_path):
    if request.param == AsyncLocalFactory:
        factory = request.param(tmp_path)
    elif request.param == GcpAsyncFactory:
        factory = request.param(bucket_name='unit-tests-001')
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