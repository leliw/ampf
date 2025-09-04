import pytest
from pydantic import BaseModel

from ampf.base import BaseAsyncQueryStorage, BaseAsyncStorage, KeyNotExistsException
from ampf.in_memory import InMemoryAsyncStorage


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def storage():
    return InMemoryAsyncStorage("test", D)

@pytest.mark.asyncio
async def test_storage_all(storage: BaseAsyncStorage):
    assert await storage.is_empty()

    d = D(name="foo", value="beer")
    await storage.put("foo", d)

    assert ["foo"] == [key async for key in storage.keys()]
    assert d == await storage.get("foo")

    assert not await storage.is_empty()

    await storage.delete("foo")
    assert [] == [key async for key in storage.keys()]
    with pytest.raises(KeyNotExistsException):
        await storage.get("foo")

    await storage.put(d.name, d)
    await storage.drop()
    assert [] == [key async for key in storage.keys()]

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
    assert ret[0].name == "foo"
    assert ret[1].name == "bar"
    # When: Get all items different than "beer"
    ret = [item async for item in storage.where("value", "!=", "beer").get_all()]
    # Then: One item is returned
    assert len(ret) == 1
    assert ret[0].name == "baz"
