import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated, Literal, Type
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel, computed_field

from ampf.base import BaseAsyncFactory
from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.dependency.dependency_registry import DependencyRegistry, get_dependency
from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from ampf.tasks.background_runner import BackgroundRunner
from ampf.tasks.direct_runner import DirectRunner
from ampf.tasks.pubsub_pull_runner import PubsubPullRunner
from ampf.tasks.pubsub_push_runner import PubsubPushRunner
from ampf.tasks.pubsub_runner import PubsubRunner
from ampf.tasks import BaseTask, TaskStatus, ManagedTaskRunner, TaskRunner, TaskRegistry
from ampf.testing import ApiTestClient

### Models ###


class TaskCreate(BaseModel):
    name: str | None = None
    value: int | None = None


# Task is subclass of BaseTask
# it has to implement result_id getter - any id referring to result of this task
class Task(BaseTask):
    value: int | None = None

    @computed_field
    @property
    def result_id(self) -> str | None:
        return str(self.id) if self.status == TaskStatus.COMPLETED else None

    @classmethod
    def create(cls, value_create: TaskCreate) -> "Task":
        return Task(id=uuid4(), **value_create.model_dump())


### Application & dependencies ###


# AppConfig has properties:
# * task_runner - which runner is used (as string) - Direct, Background, PubsubPull, PubsubPush
# * task_runner_type - which runner class is used, it is derived from task_runner string
# * processor_topic, processor_subscription - for PubsubPullRunner - which topic and subscription are used.
#   The prefix `processor` is the name of used processor (@see `@TaskRegistry.register("processor", Task)` below)
class AppConfig(BaseModel):
    task_runner: Literal["Direct", "Background", "PubsubPull", "PubsubPush"]

    processor_topic: str = "processor"
    processor_subscription: str = "processor-sub"

    @cached_property
    def task_runner_type(self) -> Type[TaskRunner]:
        match self.task_runner:
            case "Direct":
                return DirectRunner
            case "Background":
                return BackgroundRunner
            case "PubsubPush":
                return PubsubPushRunner
            case "PubsubPull":
                return PubsubPullRunner
            case _:
                raise ValueError(f"Unknown task runner type: {self.task_runner}")


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


def lifespan(app_config: AppConfig):
    # Clear initialized objects (for tests)
    DependencyRegistry.clear_objects()
    app_state = AppState.create(app_config)
    DependencyRegistry.add(app_state)
    DependencyRegistry.add(app_state.task_runner, TaskRunner)

    # Lifespan has to start TaskRunner if it is an object
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        app.state.app_state = app_state
        async with app_state.manage_lifecycle(app):
            yield

    return _lifespan


@DependencyRegistry.register
def get_storage(app_state: AppState) -> BaseAsyncStorage[Task]:
    return app_state.factory.create_storage("jobs", Task)


# Define static dependencies as FastAPI dependencies (if it is needed)
AppStateDep = Annotated[AppState, Depends(get_dependency(AppState))]
AppConfigDep = Annotated[AppConfig, Depends(get_dependency(AppConfig))]
StorageTaskDep = Annotated[BaseAsyncStorage[Task], Depends(get_dependency(BaseAsyncStorage[Task]))]


# TaskRunner is a FastAPI dependency because of BackgroundTasks parameter!
def get_task_runner(app_state: AppStateDep, background_tasks: BackgroundTasks) -> TaskRunner:
    if isinstance(app_state.task_runner, ManagedTaskRunner):
        return app_state.task_runner
    elif app_state.task_runner == BackgroundRunner:
        return BackgroundRunner(background_tasks)
    else:
        return app_state.task_runner.create()


TaskRunnerDep = Annotated[TaskRunner, Depends(get_task_runner)]


# App definition with routers
def main_app(app_config: AppConfig) -> FastAPI:

    app = FastAPI(lifespan=lifespan(app_config))

    @app.post("/api/jobs", status_code=201)
    async def post(storage: StorageTaskDep, data: TaskCreate, task_runner: TaskRunnerDep) -> Task:
        task = Task.create(data)
        await storage.create(task)
        await task_runner.run_async("processor", task)  # <--- Runs processor in background
        return task

    @app.get("/api/jobs/{id}")
    async def get(storage: StorageTaskDep, id: UUID) -> Task:
        job = await storage.get(id)
        return job

    return app


@pytest.fixture(params=["Direct", "Background", "PubsubPull", "PubsubPush"])
def app_config(request) -> AppConfig:
    return AppConfig(task_runner=request.param)


@pytest.fixture
def app(app_config: AppConfig) -> FastAPI:
    return main_app(app_config)


@pytest.fixture
def client(app: FastAPI):
    with ApiTestClient(app) as client:
        if isinstance(app.state.app_state.task_runner, PubsubPushRunner):
            # PubsubPush requires extra emulator for test
            topic: GcpTopic = app.state.app_state.task_runner.get_topic("processor")
            processor_endpoint = "/pub-sub/task-processors/processor"
            subscription = topic.create_subscription(exist_ok=True)
            subscription.clear()
            with subscription.run_push_emulator(client, processor_endpoint):
                yield client
        else:
            yield client


# Register processor of name `processor`
# Allowed parameters:
# * Non FastApi dependencies
# * payload inheriting Pydantic BaseModel
@TaskRegistry.register("processor", Task)
async def processor(storage: BaseAsyncStorage[Task], payload: Task) -> None:
    payload.status = TaskStatus.RUNNING
    await asyncio.sleep(1)
    payload.value = (payload.value or 0) + 1
    payload.status = TaskStatus.COMPLETED
    await storage.save(payload)


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_run_task_by_endpoint(client: ApiTestClient):
    # Given: An application and registered processor
    # When: Call POST endpoint with initial Task value
    task = client.post_typed("/api/jobs", 201, Task, json=TaskCreate(name="test"))
    # And: Wait for end of the process
    while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        await asyncio.sleep(0.1)
        task = client.get_typed(f"/api/jobs/{task.id}", 200, Task)
    # Then: Job is processed
    assert task.status == TaskStatus.COMPLETED
    assert task.name == "test"
    assert task.value == 1
    # And: Result_id is returned
    assert task.result_id is not None
