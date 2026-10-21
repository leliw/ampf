from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, TypeAdapter

from ampf.base.base_async_collection_storage import BaseAsyncCollectionStorage
from ampf.base.collection_def import CollectionDef
from ampf.base.exceptions import KeyNotExistsException
from ampf.cruds.crud_service import CRUDService
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory


class TCreate(BaseModel):
    name: str
    value: int


class TUpdate(BaseModel):
    name: str | None = None
    value: int | None = None


class THeader(BaseModel):
    id: UUID
    name: str
    value: int
    created_at: datetime
    updated_at: datetime


class BaseT(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    value: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class T1(BaseT):
    name: Literal["T1"] = "T1"
    value1: int = 1


class T2(BaseT):
    name: Literal["T2"] = "T2"
    value2: int = 2


T = Annotated[T1 | T2, Field(discriminator="name")]

InMemoryAsyncFactory(collection_defs=[CollectionDef("crud_t", T)])


class TCRUDService(CRUDService):
    def __init__(self, storage: BaseAsyncCollectionStorage[T]) -> None:
        super().__init__(storage, TypeAdapter(T), THeader, TCreate, TUpdate)


@pytest.fixture
def service() -> TCRUDService:
    return TCRUDService(InMemoryAsyncFactory(collection_defs=[CollectionDef("crud_t", T, "id")]).get_collection(T))


async def test_get_rows(service: TCRUDService):
    # Given: CRUD service with empty storage
    # When: Get rows
    ret = [r async for r in service.get_rows()]
    # Then: Empty list is returned
    assert len(ret) == 0


async def test_create_get(service: TCRUDService):
    # Given: CRUD service with empty storage
    # And: Value_create
    value_create = TCreate(name="T1", value=1)
    # When: Create record
    created = await service.create(value_create)
    # Then: Record is returned
    assert created.name == "T1"
    # And: Can be got by id
    got = await service.get(created.id)
    assert got.name == "T1"


async def test_create_value(service: TCRUDService):
    # Given: CRUD service with empty storage
    # And: Value
    value = T2(value=2)
    # When: Create record
    created = await service.create(value)
    # Then: Record is returned
    assert created.name == "T2"
    # And: Id is the same
    assert value.id == created.id
    # And: Can be got by id
    got = await service.get(created.id)
    assert got.name == "T2"


async def test_update_get_rows(service: TCRUDService):
    # Given: CRUD service with a record in storage
    value = T2(value=2)
    await service.create(value)
    # When: Update record
    patch = TUpdate(value=3)
    updated = await service.update(value.id, patch)
    # Then: Record is returned
    assert updated.value == 3
    assert updated.updated_at > value.updated_at
    # And: It is in list
    ret = [r async for r in service.get_rows()]
    assert ret[0].value == 3


async def test_delete_get(service: TCRUDService):
    # Given: CRUD service with a record in storage
    value = T2(value=2)
    await service.create(value)
    # When: delete record
    await service.delete(value.id)
    # Then: Record isn't returned
    with pytest.raises(KeyNotExistsException):
        await service.get(value.id)
