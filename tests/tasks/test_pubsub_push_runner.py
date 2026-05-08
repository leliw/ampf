import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory
from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.dependency.dependency_registry import DependencyRegistry
from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic
from ampf.tasks import TaskRegistry, TaskRunner
from ampf.tasks.pubsub_push_runner import PubsubPushRunner
from ampf.testing import ApiTestClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
_log = logging.getLogger()
_log.setLevel(logging.DEBUG)


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
async def test_run_process_by_endpoint():
    # Given: A registered processor
    @TaskRegistry.register("processor", Task)
    async def processor(storage: BaseAsyncStorage[Task], payload: Task) -> None:
        await asyncio.sleep(1)
        payload.value = (payload.value or 0) + 1
        payload.status = "done"
        await storage.save(payload)

    # And: An AppConfig with a topic and subscription names for this processor
    class AppConfig(BaseModel):
        processor_topic: str = "processor"

    # And: An AppState with config, factory and PubsubPullRunner
    @dataclass
    class AppState:
        config: AppConfig
        factory: BaseAsyncFactory
        task_runner: PubsubPushRunner

        @classmethod
        def create(cls, config: AppConfig):
            factory = GcpAsyncFactory()
            task_runner = PubsubPushRunner.create(factory, config)
            return cls(config=config, factory=factory, task_runner=task_runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_state = AppState.create(config=AppConfig())
        app.state.app_state = app_state
        DependencyRegistry.add(app_state)
        async with app_state.task_runner.manage_lifecycle(app):
            yield

    def get_app_state(request: Request) -> AppState:
        return request.app.state.app_state

    AppStateDep = Annotated[AppState, Depends(get_app_state)]

    def get_task_runner(app_state: AppStateDep) -> TaskRunner:  # pyright: ignore[reportInvalidTypeForm]
        return app_state.task_runner

    # And: A defined TaskRunnerDep
    TaskRunnerDep = Annotated[TaskRunner, Depends(get_task_runner)]
    # And: An application with endpoints POST and GET
    app = FastAPI(lifespan=lifespan)

    @DependencyRegistry.register
    def get_storage(app_state: AppStateDep) -> BaseAsyncStorage[Task]:  # pyright: ignore[reportInvalidTypeForm]
        return app_state.factory.create_storage("jobs", Task)

    StorageTaskDep = Annotated[BaseAsyncStorage[Task], Depends(get_storage)]

    @app.post("/api/jobs", status_code=201)
    async def post(storage: StorageTaskDep, data: TaskCreate, task_runner: TaskRunnerDep) -> Task:  # type: ignore
        task = Task.create(data)
        await storage.create(task)
        await task_runner.run_async("processor", task)  # <--- Runs processor in background
        return task

    @app.get("/api/jobs/{id}")
    async def get(storage: StorageTaskDep, id: UUID) -> Task:  # type: ignore
        job = await storage.get(id)
        return job

    with ApiTestClient(app) as client:
        topic: GcpTopic = app.state.app_state.task_runner.get_topic("processor")
        subscription = topic.create_subscription(exist_ok=True)
        subscription.clear()
        processor_endpoint = "/pub-sub/task-processors/processor"
        response = client.get("/openapi.json", 200)
        open_api = json.loads(response.text)
        assert processor_endpoint in open_api["paths"]
        with subscription.run_push_emulator(client, processor_endpoint):
            # When: Call POST endpoint with initial Task value
            task = client.post_typed("/api/jobs", 201, Task, json=TaskCreate(name="test"))
            # And: Wait for end of the process
            while task.status == "processing":
                await asyncio.sleep(0.1)
                task = client.get_typed(f"/api/jobs/{task.id}", 200, Task)
            # Then: Job is processed
            assert task.status == "done"
            assert task.name == "test"
            assert task.value == 1
