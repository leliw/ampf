import asyncio
from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID, uuid4

from ampf.base import BaseAsyncFactory
from ampf.gcp import GcpAsyncFactory
from fastapi.concurrency import asynccontextmanager
import pytest
from ampf.in_memory import InMemoryFactory
from ampf.testing import ApiTestClient
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from ampf.processors.pubsub_pull_runner import PubsubPullRunner
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
# @pytest.mark.parametrize("runner_type", [DirectRunner, BackgroundRunner])
# async def test_run_process_by_endpoint(runner_type: Type[TaskRunner]):
async def test_run_process_by_endpoint():
    # Given: A registerd processor
    @TaskRegistry.register("processor", Task)
    async def processor(payload: Task) -> None:
        await asyncio.sleep(1)
        payload.value = (payload.value or 0) + 1
        payload.status = "done"
        storage.save(payload)

    # And: An AppConfig with a topic and subscription names for this processor
    class AppConfig(BaseModel):
        processor_topic: str = "processor"
        processor_subscription: str = "processor-sub"

    # And: An AppState with config, factory and PubsubPullRunner
    @dataclass
    class AppState:
        config: AppConfig
        factory: BaseAsyncFactory
        task_runner: PubsubPullRunner

        @classmethod
        def create(cls, config: AppConfig):
            config = AppConfig()
            factory = GcpAsyncFactory()
            task_runner = PubsubPullRunner.create(factory, config)
            return cls(config=config, factory=factory, task_runner=task_runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_state = AppState.create(config = AppConfig())
        app.state.app_state = app_state
        async with app_state.task_runner:
            yield

    def get_app_state(request: Request) -> AppState:
        return request.app.state.app_state
    AppStateDep = Annotated[AppState, Depends(get_app_state)]
    
    def get_task_runner(app_state: AppStateDep) -> TaskRunner: # type: ignore
        return app_state.task_runner

    # And: A defined TaskRunnerDep
    TaskRunnerDep = Annotated[TaskRunner, Depends(get_task_runner)]
    # And: An application with endpoints POST and GET
    app = FastAPI(lifespan=lifespan)
    storage = InMemoryFactory().create_storage("jobs", Task)

    @app.post("/api/jobs", status_code=201)
    async def post(data: TaskCreate, task_runner: TaskRunnerDep) -> Task:  # type: ignore
        task = Task.create(data)
        storage.create(task)
        await task_runner.run_async("processor", task)  # <--- Runs processor in background
        return task

    @app.get("/api/jobs/{id}")
    async def get(id: UUID) -> Task:
        job = storage.get(id)
        return job

    with ApiTestClient(app) as client:
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
