from typing import Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from ampf.gcp import GcpStorage
from ampf.gcp.gcp_async_storage import GcpAsyncStorage
from ampf.gcp.gcp_factory import GcpFactory


class TC(BaseModel):
    name: str
    embedding: Optional[List[float]] = None


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str


class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    tasks_l: List[Task] = Field(default_factory=list)
    tasks_d: Dict[UUID, Task] = Field(default_factory=dict)


@pytest.fixture()
def storage(gcp_factory: GcpFactory, collection_name: str):
    storage = gcp_factory.create_storage(collection_name, TC)
    yield storage
    storage.drop()


@pytest.fixture()
async def async_storage(gcp_factory: GcpFactory, collection_name: str):
    storage = GcpAsyncStorage(collection_name, TC)
    yield storage
    await storage.drop()


@pytest.fixture()
def job_storage(gcp_factory: GcpFactory, collection_name: str):
    storage = gcp_factory.create_storage(collection_name, Job)
    yield storage
    storage.drop()


@pytest.fixture()
async def async_job_storage(gcp_factory: GcpFactory, collection_name: str):
    storage = GcpAsyncStorage(collection_name, Job)
    yield storage
    await storage.drop()


def test_storage(storage: GcpStorage[TC]):
    storage.put("test", TC(name="test"))

    assert storage.get("test") == TC(name="test")
    assert list(storage.keys()) == ["test"]
    assert list(storage.get_all()) == [TC(name="test")]

    storage.delete("test")

    assert list(storage.keys()) == []

    storage.put("test2", TC(name="test2"))
    storage.put("test3", TC(name="test3"))
    storage.drop()

    assert list(storage.keys()) == []


"""
This test requires vector index to be created.

gcloud firestore indexes composite create --project=development-428212 --collection-group=tests-ampf-gcp --query-scope=COLLECTION --field-config=vector-config='{"dimension":"3","flat": "{}"}',field-path=embedding
"""


def test_embedding(storage: GcpStorage[TC]):
    # Given: Data with embedding
    tc1 = TC(name="test1", embedding=[1.0, 2.0, 3.0])
    tc2 = TC(name="test2", embedding=[4.0, 5.0, 6.0])
    # When: Save them
    storage.put("1", tc1)
    storage.put("2", tc2)
    # And: Find nearest
    nearest = list(storage.find_nearest(tc1.embedding or []))
    # Then: All two are returned
    assert len(nearest) == 2
    # And: The nearest is the first one
    assert nearest[0] == tc1
    # And: The second is the second
    assert nearest[1] == tc2


@pytest.mark.asyncio()
async def test_async_embedding(async_storage: GcpAsyncStorage[TC]):
    # Given: Data with embedding
    tc1 = TC(name="test1", embedding=[1.0, 2.0, 3.0])
    tc2 = TC(name="test2", embedding=[4.0, 5.0, 6.0])
    # When: Save them
    await async_storage.put("test1", tc1)
    await async_storage.put("test2", tc2)
    # And: Find nearest
    nearest = list([x async for x in async_storage.find_nearest(tc1.embedding or [])])
    # Then: All two are returned
    assert len(nearest) == 2
    # And: The nearest is the first one
    assert nearest[0] == tc1
    # And: The second is the second
    assert nearest[1] == tc2

"""
This test requires vector index to be created.

gcloud firestore indexes composite create --project=development-428212 --collection-group=tests-ampf-gcp --query-scope=COLLECTION --field-config=order=ASCENDING,field-path=name --field-config=vector-config='{"dimension":"3","flat": "{}"}',field-path=embedding
"""
@pytest.mark.asyncio()
async def test_async_where_embedding(async_storage: GcpAsyncStorage[TC]):
    # Given: Data with embedding
    tc1 = TC(name="test1", embedding=[1.0, 2.0, 3.0])
    tc2 = TC(name="test2", embedding=[4.0, 5.0, 6.0])
    # When: Save them
    await async_storage.put("test1", tc1)
    await async_storage.put("test2", tc2)
    # And: Find nearest
    nearest = list([x async for x in async_storage.where("name", "==", "test1").find_nearest(tc1.embedding or [])])
    # Then: All two are returned
    assert len(nearest) == 1
    # And: The nearest is the first one
    assert nearest[0] == tc1


def test_uuid_saving(job_storage: GcpStorage[Job]):
    # Given: A job with a task
    t = Task(name="test")
    j = Job(name="test", tasks_l=[t], tasks_d={t.id: t})
    # When: Save it
    job_storage.save(j)
    # Then: It is saved
    assert job_storage.get(j.id) == j

@pytest.mark.asyncio()
async def test_uuid_async_saving(async_job_storage: GcpAsyncStorage[Job]):
    # Given: A job with a task
    t = Task(name="test")
    j = Job(name="test", tasks_l=[t], tasks_d={t.id: t})
    # When: Save it
    await async_job_storage.save(j)
    # Then: It is saved
    assert await async_job_storage.get(j.id) == j