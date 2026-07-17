import asyncio
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
import pytest

from ampf.gcp import GcpAsyncFactory
from tests.gcp.conftest import AppConfig


class D(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    name: str


@pytest.mark.asyncio
async def test_two_databases(config: AppConfig):
    # Given: Two factories
    factory1 = GcpAsyncFactory(database=config.gcp_database_1, project_id=config.project_id)
    factory2 = GcpAsyncFactory(database=config.gcp_database_2, project_id=config.project_id)
    # And: Two storages
    storage1 = factory1.create_storage("test", D)
    storage2 = factory2.create_storage("test", D)
    # When: Two records are created in different storages
    rec1 = D(name="t1")
    rec2 = D(name="t2")
    await storage1.create(rec1)
    await storage2.create(rec2)
    # Then: The storages are separated
    assert await storage1.key_exists(rec1.uuid)
    assert not await storage2.key_exists(rec1.uuid)
    assert await storage2.key_exists(rec2.uuid)
    assert not await storage1.key_exists(rec2.uuid)
    # CleanUp:
    asyncio.gather(storage1.drop(), storage2.drop())
