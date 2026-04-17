from typing import List, Optional
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from ampf.base.base_query_storage import BaseQueryStorage
from ampf.gcp import GcpStorage
from ampf.in_memory import InMemoryStorage
from ampf.local import JsonMultiFilesStorage, JsonOneFileStorage


class D(BaseModel):
    name: str
    value: str
    embedding: Optional[List[float]] = None
    tags: Optional[List[str]] = None


class Duuid(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    name: str
    value: str


@pytest.fixture(params=[InMemoryStorage, JsonOneFileStorage, JsonMultiFilesStorage, GcpStorage])
def storage(gcp_factory, request, tmp_path):
    if request.param in [JsonOneFileStorage, JsonMultiFilesStorage]:
        storage = request.param("test", D, root_path=tmp_path)
    elif request.param == GcpStorage:
        storage = gcp_factory.create_storage("test", D)
    else:
        storage = request.param("test", D)
    yield storage
    storage.drop()


@pytest.fixture(params=[InMemoryStorage, JsonOneFileStorage, JsonMultiFilesStorage, GcpStorage])
def storage_key(gcp_factory, request, tmp_path):
    if request.param in [JsonOneFileStorage, JsonMultiFilesStorage]:
        storage = request.param("test", D, key=lambda d: d.value, root_path=tmp_path)
    elif request.param == GcpStorage:
        storage = gcp_factory.create_storage("test", D, key=lambda d: d.value)
    else:
        storage = request.param("test", D, key=lambda d: d.value)
    yield storage
    storage.drop()


@pytest.fixture(params=[InMemoryStorage, JsonOneFileStorage, JsonMultiFilesStorage, GcpStorage])
def storage_uuid(gcp_factory, request, tmp_path):
    if request.param in [JsonOneFileStorage, JsonMultiFilesStorage]:
        storage = request.param("test", Duuid, root_path=tmp_path)
    elif request.param == GcpStorage:
        storage = gcp_factory.create_storage("test", Duuid)
    else:
        storage = request.param("test", Duuid)
    yield storage
    storage.drop()


def test_query(storage: BaseQueryStorage):
    # Given: Stored two elements with the same value and one with other
    storage.save(D(name="foo", value="beer"))
    storage.save(D(name="bar", value="beer"))
    storage.save(D(name="baz", value="wine"))
    # When: Get all items with "beer"
    ret = list(storage.where("value", "==", "beer").get_all())
    # Then: Two items are returned
    assert len(ret) == 2
    assert ret[0].name in ["foo", "bar"]
    assert ret[1].name in ["foo", "bar"]
    # When: Get all items different than "beer"
    ret = list(storage.where("value", "!=", "beer").get_all())
    # Then: One item is returned
    assert len(ret) == 1
    assert ret[0].name == "baz"


def test_query_uuid(storage_uuid: BaseQueryStorage):
    # Given: A stred element with UUID filed
    d = Duuid(name="foo", value="beer")
    storage_uuid.create(d)
    # When: Filter by UUID
    ret = [item for item in storage_uuid.where("uuid", "==", d.uuid).get_all()]
    # Then: The element is returned
    assert len(ret) == 1


def test_query_array_contains_any(storage: BaseQueryStorage):
    storage.save(D(name="d1", value="v1", tags=["tag1", "tag2"]))
    storage.save(D(name="d2", value="v2", tags=["tag2", "tag3"]))
    storage.save(D(name="d3", value="v3", tags=["tag4"]))

    result = list(storage.where("tags", "array_contains_any", ["tag1", "tag4"]).get_all())
    assert len(result) == 2
    assert {r.name for r in result} == {"d1", "d3"}

    result = list(storage.where("tags", "array_contains_any", ["tag5"]).get_all())
    assert len(result) == 0
