from typing import List, Optional, Type
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from ampf.base import BaseAsyncStorage
from ampf.base.base_async_query_storage import BaseAsyncQueryStorage
from ampf.gcp import GcpAsyncStorage
from ampf.in_memory import InMemoryAsyncStorage
from ampf.local import JsonMultiFilesAsyncStorage, JsonOneFileAsyncStorage


class D(BaseModel):
    name: str
    value: str
    embedding: Optional[List[float]] = None
    tags: Optional[List[str]] = None


class Duuid(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    name: str
    value: str


@pytest.fixture(
    params=[
        InMemoryAsyncStorage,
        JsonOneFileAsyncStorage,
        JsonMultiFilesAsyncStorage,
        GcpAsyncStorage,
    ]
)
async def storage(gcp_factory, request, tmp_path):
    clazz: Type[BaseAsyncStorage[D]] = request.param
    if clazz in [JsonOneFileAsyncStorage, JsonMultiFilesAsyncStorage]:
        storage = clazz("tests-ampf-gcp", D, root_path=tmp_path)  # type: ignore
    else:
        storage = clazz("tests-ampf-gcp", D)
    yield storage
    await storage.drop()


@pytest.fixture(
    params=[
        InMemoryAsyncStorage,
        JsonOneFileAsyncStorage,
        JsonMultiFilesAsyncStorage,
        GcpAsyncStorage,
    ]
)
async def storage_uuid(request, tmp_path):
    clazz: Type[BaseAsyncStorage[Duuid]] = request.param
    if clazz in [JsonOneFileAsyncStorage, JsonMultiFilesAsyncStorage]:
        storage = clazz("tests-ampf-gcp", Duuid, root_path=tmp_path)  # type: ignore
    else:
        storage = clazz("tests-ampf-gcp", Duuid)
    yield storage
    await storage.drop()


@pytest.mark.asyncio
async def test_query(storage: BaseAsyncQueryStorage):
    # Given: Stored two elements with the same value and one with other
    await storage.save(D(name="foo", value="beer"))
    await storage.save(D(name="bar", value="beer"))
    await storage.save(D(name="baz", value="wine"))
    # When: Get all items with "beer"
    ret = [item async for item in storage.where("value", "==", "beer").get_all()]
    # Then: Two items are returned
    assert len(ret) == 2
    assert ret[0].name in ["foo", "bar"]
    assert ret[1].name in ["foo", "bar"]
    # When: Get all items different than "beer"
    ret = [item async for item in storage.where("value", "!=", "beer").get_all()]
    # Then: One item is returned
    assert len(ret) == 1
    assert ret[0].name == "baz"


@pytest.mark.asyncio
async def test_query_uuid(storage_uuid: BaseAsyncQueryStorage):
    # Given: A stred element with UUID filed
    d = Duuid(name="foo", value="beer")
    await storage_uuid.create(d)
    # When: Filter by UUID
    ret = [item async for item in storage_uuid.where("uuid", "==", d.uuid).get_all()]
    # Then: The element is returned
    assert len(ret) == 1

@pytest.mark.asyncio
async def test_query_array_contains_any(storage: BaseAsyncQueryStorage):
    await storage.save(D(name="d1", value="v1", tags=["tag1", "tag2"]))
    await storage.save(D(name="d2", value="v2", tags=["tag2", "tag3"]))
    await storage.save(D(name="d3", value="v3", tags=["tag4"]))

    result = [item async for item in storage.where("tags", "array_contains_any", ["tag1", "tag4"]).get_all()]
    assert len(result) == 2
    assert {r.name for r in result} == {"d1", "d3"}

    result = [item async for item in storage.where("tags", "array_contains_any", ["tag5"]).get_all()]
    assert len(result) == 0
