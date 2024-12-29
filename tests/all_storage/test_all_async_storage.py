from pydantic import BaseModel
import pytest

from ampf.base import BaseAsyncStorage, KeyExistsException
from ampf.gcp import GcpAsyncStorage
from ampf.in_memory import InMemoryAsyncStorage
from ampf.local import FileStorage
from ampf.async_local import JsonOneFileAsyncStorage, JsonMultiFilesAsyncStorage


class D(BaseModel):
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
def storage(request, tmp_path):
    if request.param in [JsonOneFileAsyncStorage, JsonMultiFilesAsyncStorage]:
        FileStorage._root_dir_path = tmp_path
    storage = request.param("test", D)
    yield storage
    # storage.drop()


@pytest.mark.asyncio
async def test_put_and_get(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I create it
    await storage.put("foo", d)
    # Then: Is created
    assert d == await storage.get("foo")
    await storage.drop()


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
    await storage.drop()


@pytest.mark.asyncio
async def test_create_new(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I create it
    await storage.create(d)
    # Then: Is created
    assert ["foo"] == [key async for key in storage.keys()]
    await storage.drop()


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
    await storage.drop()


@pytest.mark.asyncio
async def test_save_not_exists(storage: BaseAsyncStorage):
    # Given: A new element
    d = D(name="foo", value="beer")
    # When: I save it
    await storage.save(d)
    # Then: Is saved
    assert ["foo"] == [key async for key in storage.keys()]
    await storage.drop()


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
    await storage.drop()


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
    await storage.drop()


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
    await storage.drop()


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
    await storage.drop()


@pytest.mark.asyncio
async def test_is_empty(storage: BaseAsyncStorage):
    # Given: An empty storage
    assert await storage.is_empty()
    # When: I add an element
    d = D(name="foo", value="beer")
    await storage.save(d)
    # Then: Is not empty
    assert not await storage.is_empty()
    await storage.drop()
