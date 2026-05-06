import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal, Type
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory
from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.dependency.dependency_registry import DependencyRegistry
from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from ampf.processors.background_runner import BackgroundRunner
from ampf.processors.direct_runner import DirectRunner
from ampf.processors.pubsub_pull_runner import PubsubPullRunner
from ampf.processors.pubsub_push_runner import PubsubPushRunner
from ampf.processors.pubsub_runner import PubsubRunner
from ampf.processors.task_model import ManagedTaskRunner, TaskRunner
from ampf.processors.task_registry import TaskRegistry
from ampf.testing import ApiTestClient


# AppConfig has properties:
# * task_runner_type - which runner is used
# * processor_topic, processor_subscription - for PubsubPullRunner - which topic and subscription are used.
#   The prefix `processor` is the name of used processor
class AppConfig(BaseModel):
    task_runner_type: Type[TaskRunner] = DirectRunner

    processor_topic: str = "processor"
    processor_subscription: str = "processor-sub"


# AppState has a property:
# * task_runner - if TaskRunner is AsyncContextManager it is an object, otherwise it is a class
@dataclass
class AppState:
    config: AppConfig
    factory: BaseAsyncFactory
    task_runner: TaskRunner | Type[TaskRunner]

    @classmethod
    def create(cls, config: AppConfig):
        if issubclass(config.task_runner_type, PubsubRunner):
            factory = GcpAsyncFactory()  # Required by PubsubRunner
            task_runner = config.task_runner_type.create(factory, config)
        else:
            factory = InMemoryAsyncFactory()
            task_runner = config.task_runner_type
        return cls(config=config, factory=factory, task_runner=task_runner)

    @asynccontextmanager
    async def manage_lifecycle(self, app: FastAPI):
        if isinstance(self.task_runner, ManagedTaskRunner):
            async with self.task_runner.manage_lifecycle(app):
                yield self
        else:
            yield self


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


@pytest.fixture(params=[DirectRunner, BackgroundRunner, PubsubPullRunner, PubsubPushRunner])
def app_config(request) -> AppConfig:
    return AppConfig(task_runner_type=request.param)


@pytest.fixture
def app(app_config: AppConfig) -> FastAPI:

    DependencyRegistry.clear()

    # Lifespan has to start TaskRunner if it is an object
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_state = AppState.create(config=app_config)
        DependencyRegistry.add(app_state)
        app.state.app_state = app_state
        async with app_state.manage_lifecycle(app):
            yield

    def get_app_state(request: Request) -> AppState:
        return request.app.state.app_state

    AppStateDep = Annotated[AppState, Depends(get_app_state)]

    # TaskRunner FastAPI dependency provides an object to run task
    # * it can be got from AppState if it is an object
    # * if it is BackgroundRunner then it uses BackgroundTasks dependency
    # * otherwise just create from given class
    def get_task_runner(app_state: AppStateDep, background_tasks: BackgroundTasks) -> TaskRunner:  # type: ignore
        if isinstance(app_state.task_runner, ManagedTaskRunner):
            return app_state.task_runner
        elif app_state.task_runner == BackgroundRunner:
            return BackgroundRunner(background_tasks)
        else:
            return app_state.task_runner.create()

    TaskRunnerDep = Annotated[TaskRunner, Depends(get_task_runner)]

    # Register non FastAPI dependency used by processor
    @DependencyRegistry.register
    def get_storage(app_state: AppStateDep) -> BaseAsyncStorage[Task]:  # type: ignore
        return app_state.factory.create_storage("jobs", Task)

    StorageTaskDep = Annotated[BaseAsyncStorage[Task], Depends(get_storage)]

    # Register processor of name `processor`
    # Allowed parameters:
    # * Non FastApi dependencies
    # * payload inheriting Pydantic BaseModel
    @TaskRegistry.register("processor", Task)
    async def processor(storage: BaseAsyncStorage[Task], payload: Task) -> None:
        await asyncio.sleep(1)
        payload.value = (payload.value or 0) + 1
        payload.status = "done"
        await storage.save(payload)

    app = FastAPI(lifespan=lifespan)

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

    return app


@pytest.fixture
def client(app: FastAPI) -> ApiTestClient:  # type: ignore
    with ApiTestClient(app) as client:
        if isinstance(app.state.app_state.task_runner, PubsubPushRunner):
            # PubsubPush requires extra emulator for test
            topic: GcpTopic = app.state.app_state.task_runner.get_topic("processor")
            processor_endpoint = '/pub-sub/task-processors/processor'
            subscription = topic.create_subscription(exist_ok=True)
            subscription.clear()
            with subscription.run_push_emulator(client, processor_endpoint):
                yield client # type: ignore
        else:
            yield client # type: ignore

@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_run_process_by_endpoint(client: ApiTestClient):
    # Given: An application with processor
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
