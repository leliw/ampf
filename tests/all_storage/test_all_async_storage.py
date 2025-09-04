import logging
from typing import List, Optional, Type
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from ampf.base import BaseAsyncStorage, KeyExistsException
from ampf.base.base_async_query_storage import BaseAsyncQueryStorage
from ampf.gcp import GcpAsyncStorage
from ampf.in_memory import InMemoryAsyncStorage
from ampf.local_async import JsonMultiFilesAsyncStorage, JsonOneFileAsyncStorage

_log = logging.getLogger(__name__)


class D(BaseModel):
    name: str
    value: str
    embedding: Optional[List[float]] = None


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
async def test_put_and_get(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I create it
    await storage.put("foo", d)
    # Then: Is created
    assert d == await storage.get("foo")


@pytest.mark.asyncio
async def test_keys(storage: BaseAsyncStorage):
    # Given: Some elements
    d1 = D(name="foo", value="beer")
    d2 = D(name="bar", value="wine")
    await storage.put("foo", d1)
    await storage.put("bar", d2)
    # When: I get all keys
    keys = [key async for key in storage.keys()]
    # Then: All keys are returned
    assert "foo" in keys
    assert "bar" in keys
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_create_new(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I create it
    await storage.create(d)
    # Then: Is created
    assert ["foo"] == [key async for key in storage.keys()]


@pytest.mark.asyncio
async def test_create_already_exists(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # And: It is already created
    await storage.create(d)
    # When:
    # I try to create it again
    with pytest.raises(KeyExistsException):
        await storage.create(d)


@pytest.mark.asyncio
async def test_save_not_exists(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I save it
    await storage.save(d)
    # Then: Is saved
    assert ["foo"] == [key async for key in storage.keys()]


@pytest.mark.asyncio
async def test_save_exists(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # And: It is already saved
    await storage.save(d)
    # When: I save it again
    await storage.save(d)
    # Then: Is saved
    assert ["foo"] == [key async for key in storage.keys()]


@pytest.mark.asyncio
async def test_delete_existing(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # And: It is already saved
    await storage.save(d)
    # When: I delete it
    await storage.delete("foo")
    # Then: It is not exist
    assert not await storage.key_exists("foo")


@pytest.mark.asyncio
async def test_get_all(storage: BaseAsyncStorage):
    # Given: Some elements
    d1 = D(name="foo", value="beer")
    d2 = D(name="bar", value="wine")
    await storage.save(d1)
    await storage.save(d2)
    # When: I get all elements
    all_elements = [e async for e in storage.get_all()]
    # Then: All elements are returned
    assert d1 in all_elements
    assert d2 in all_elements
    assert len(all_elements) == 2


@pytest.mark.asyncio
async def test_key_exists(storage: BaseAsyncStorage):
    # Given: Some elements
    d1 = D(name="foo", value="beer")
    d2 = D(name="bar", value="wine")
    await storage.save(d1)
    await storage.save(d2)
    # When: I check if key exists
    assert await storage.key_exists("foo")
    assert not await storage.key_exists("baz")


@pytest.mark.asyncio
async def test_is_empty(storage: BaseAsyncStorage):
    # Given: An empty storage
    assert await storage.is_empty()
    # When: I add an element
    d = D(name="foo", value="beer")
    await storage.save(d)
    # Then: Is not empty
    assert not await storage.is_empty()


@pytest.mark.asyncio
async def test_uuid(storage_uuid: BaseAsyncStorage):
    d = Duuid(name="foo", value="beer")
    await storage_uuid.create(d)
    o = await storage_uuid.get(d.uuid)
    assert d == o
    o.value = "wine"
    await storage_uuid.put(o.uuid, o)
    assert o == await storage_uuid.get(o.uuid)
    await storage_uuid.delete(d.uuid)
    assert not await storage_uuid.key_exists(d.uuid)


@pytest.mark.asyncio
async def test_embedding(storage: BaseAsyncStorage[D]):
    # Given: Data with embedding
    tc1 = D(name="test1", value="1", embedding=[1.0, 2.0, 3.0])
    tc2 = D(name="test2", value="2", embedding=[4.0, 5.0, 6.0])
    # When: Save them
    await storage.put("test1", tc1)
    await storage.put("test2", tc2)
    # And: Find nearest
    nearest = [item async for item in storage.find_nearest(tc1.embedding or [])]
    # Then: All two are returned
    assert len(nearest) == 2
    # And: The nearest is the first one
    assert nearest[0] == tc1
    # And: The second is the second
    assert nearest[1] == tc2

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
    # When: Filrter by UUID
    ret = [item async for item in storage_uuid.where("uuid", "==", d.uuid).get_all()]
    # Then: The element is returned
    assert len(ret) == 1