from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from ampf.base.base_async_collection_storage import BaseAsyncCollectionStorage
from ampf.base.collection_def import CollectionDef
from ampf.base.exceptions import KeyNotExistsException
from ampf.cruds.crud_model import CRUDRecord
from ampf.cruds.crud_service import CRUDService
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory


class TCreate(BaseModel):
    name: str
    value: int


class TPatch(BaseModel):
    name: str | None = None
    value: int | None = None


class THeader(BaseModel):
    id: UUID
    name: str
    value: int
    created_at: datetime
    updated_at: datetime


class T(CRUDRecord[THeader, TCreate, TPatch]):
    id: UUID = Field(default_factory=uuid4)
    name: str
    value: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(cls, value_create: TCreate) -> Self:
        return cls.model_validate(value_create.model_dump())

    def to_header(self) -> THeader:
        return THeader.model_validate(self.model_dump(), extra="ignore")


InMemoryAsyncFactory(collection_defs=[CollectionDef("crud_t", T)])


class TCRUDService(CRUDService[T, THeader, TCreate, TPatch]):
    def __init__(self, storage: BaseAsyncCollectionStorage[T]) -> None:
        super().__init__(storage, T)


@pytest.fixture
def service() -> TCRUDService:
    return TCRUDService(InMemoryAsyncFactory(collection_defs=[CollectionDef("crud_t", T)]).get_collection(T))


async def test_get_rows(service: TCRUDService):
    # Given: CRUD service with empty storage
    # When: Get rows
    ret = [r async for r in service.get_rows()]
    # Then: Empty list is returned
    assert len(ret) == 0


async def test_create_get(service: TCRUDService):
    # Given: CRUD service with empty storage
    # And: Value_create
    value_create = TCreate(name="x", value=1)
    # When: Create record
    created = await service.create(value_create)
    # Then: Record is returned
    assert created.name == "x"
    # And: Can be got by id
    got = await service.get(created.id)
    assert got.name == "x"


async def test_create_value(service: TCRUDService):
    # Given: CRUD service with empty storage
    # And: Value
    value = T(name="y", value=2)
    # When: Create record
    created = await service.create(value)
    # Then: Record is returned
    assert created.name == "y"
    # And: Id is the same
    assert value.id == created.id
    # And: Can be got by id
    got = await service.get(created.id)
    assert got.name == "y"


async def test_update_get_rows(service: TCRUDService):
    # Given: CRUD service with a record in storage
    value = T(name="y", value=2)
    await service.create(value)
    # When: Update record
    patch = TPatch(name="z")
    updated = await service.update(value.id, patch)
    # Then: Record is returned
    assert updated.name == "z"
    assert updated.updated_at > value.updated_at
    # And: It is in list
    ret = [r async for r in service.get_rows()]
    assert ret[0].name == "z"


async def test_delete_get(service: TCRUDService):
    # Given: CRUD service with a record in storage
    value = T(name="y", value=2)
    await service.create(value)
    # When: delete record
    await service.delete(value.id)
    # Then: Record isn't returned
    with pytest.raises(KeyNotExistsException):
        await service.get(value.id)
