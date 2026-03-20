import asyncio
from typing import Annotated, Literal, Type
from uuid import UUID, uuid4

import pytest
from ampf.in_memory import InMemoryFactory
from ampf.testing import ApiTestClient
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from ampf.processors.background_runner import BackgroundRunner
from ampf.processors.direct_runner import DirectRunner
from ampf.processors.task_model import TaskRegistry, TaskRunner


class TaskCreate(BaseModel):
    name: str | None = None
    value: int | None = None


class Task(BaseModel):
    id: UUID
    status: Literal["processing", "done", "error"]
    name: str | None = None
    value: int | None = None

    @classmethod
    def create(cls, value_create: TaskCreate) -> "Task":
        return Task(id=uuid4(), status="processing", **value_create.model_dump())


@pytest.mark.timeout(10)
@pytest.mark.asyncio
@pytest.mark.parametrize("runner_type", [DirectRunner, BackgroundRunner])
async def test_run_process_by_endpoint(runner_type: Type[TaskRunner]):
    # Given: A registerd processor
    @TaskRegistry.register("processor")
    async def processor(payload: Task) -> None:
        await asyncio.sleep(1)
        payload.value = (payload.value or 0) + 1
        payload.status = "done"
        storage.save(payload)

    # And: A defined TaskRunner
    TaskRunnerDep = Annotated[TaskRunner, Depends(runner_type.create)]
    # And: An application with endpoints POST and GET
    app = FastAPI()
    storage = InMemoryFactory().create_storage("jobs", Task)

    @app.post("/api/jobs", status_code=201)
    async def post(data: TaskCreate, task_runner: TaskRunnerDep) -> Task:  # type: ignore
        task = Task.create(data)
        storage.create(task)
        await task_runner.run_async("processor", task) # <--- Runs processor in background
        return task

    @app.get("/api/jobs/{id}")
    async def get(id: UUID) -> Task:
        job = storage.get(id)
        return job

    client = ApiTestClient(app)
    # When: Call POST endpoint
    task = client.post_typed("/api/jobs", 201, Task, json=TaskCreate(name="test"))
    # And: Wait for end of the process
    while task.status == "processing":
        await asyncio.sleep(0.1)
        task = client.get_typed(f"/api/jobs/{task.id}", 200, Task)
    # Then: Job is processed
    assert task.status == "done"
    assert task.name == "test"
    assert task.value == 1
