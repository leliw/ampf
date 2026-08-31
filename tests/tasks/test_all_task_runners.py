import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.dependency.dependency_container import DependencyContainer
from ampf.dependency.dependency_registry import DependencyRegistry
from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from ampf.tasks import BaseTask, TaskRegistry, TaskRunner, TaskStatus
from ampf.tasks.pubsub_push_runner import PubsubPushRunner
from ampf.tasks.tasks_app import TasksAppState, get_dependency_container
from ampf.testing import ApiTestClient

### Models ###


class MyTaskCreate(BaseModel):
    name: str | None = None
    value: int | None = None


# Task is subclass of BaseTask
# it has to implement result_id getter - any id referring to result of this task
class MyTask(BaseTask):
    value: int | None = None

    @classmethod
    def create(cls, value_create: MyTaskCreate) -> "MyTask":
        return MyTask(id=uuid4(), **value_create.model_dump())


### Application & dependencies ###


# AppConfig has properties:
# * task_runner - which runner is used (as string) - Direct, Background, PubsubPull, PubsubPush
# * processor_topic, processor_subscription - for PubsubPullRunner - which topic and subscription are used.
#   The prefix `processor` is the name of used processor (@see `@TaskRegistry.register("processor", Task)` below)
class AppConfig(BaseSettings):
    task_runner: Literal["Direct", "Background", "PubsubPull", "PubsubPush"]
    processor_topic: str = "processor"
    processor_subscription: str = "processor-sub"


# AppState has a property:
# * task_runner - if TaskRunner is AsyncContextManager it is an object, otherwise it is a class
@dataclass
class AppState(TasksAppState):
    @classmethod
    def create(cls, config: AppConfig) -> Self:
        if config.task_runner.startswith("Pubsub"):
            factory = GcpAsyncFactory()  # Required by PubsubRunner
        else:
            factory = InMemoryAsyncFactory()
        return cls(config=config, factory=factory)


def lifespan(app_config: AppConfig):
    # Clear initialized objects (for tests)
    DependencyRegistry.clear_objects()
    app_state = AppState.create(app_config)
    DependencyRegistry.add_all(app_state)
    DependencyRegistry.add(app_state, TasksAppState)

    # Lifespan has to start TaskRunner if it is an object
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        app.state.app_state = app_state
        async with app_state.manage_lifecycle(app):
            yield

    return _lifespan


@DependencyRegistry.register
def get_storage(factory: BaseAsyncFactory) -> BaseAsyncStorage[MyTask]:
    return factory.create_storage("jobs", MyTask)


DependencyContainerDep = Annotated[DependencyContainer, Depends(get_dependency_container)]


# App definition with routers
def main_app(app_config: AppConfig) -> FastAPI:

    app = FastAPI(lifespan=lifespan(app_config))

    @app.post("/api/tasks", status_code=201)
    async def post(dc: DependencyContainerDep, data: MyTaskCreate) -> MyTask:
        storage = dc.get(BaseAsyncStorage[MyTask])
        task_runner = dc.get(TaskRunner)
        task = MyTask.create(data)
        await storage.create(task)
        await task_runner.run_async("processor", task)  # <--- Runs processor in background
        return task

    @app.get("/api/tasks/{id}")
    async def get(dc: DependencyContainerDep, id: UUID) -> MyTask:
        storage = dc.get(BaseAsyncStorage[MyTask])
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
@TaskRegistry.register("processor", MyTask)
async def processor(storage: BaseAsyncStorage[MyTask], payload: MyTask) -> None:
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
    task = client.post_typed("/api/tasks", 201, MyTask, json=MyTaskCreate(name="test"))
    # And: Wait for end of the process
    while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        await asyncio.sleep(0.1)
        task = client.get_typed(f"/api/tasks/{task.id}", 200, MyTask)
    # Then: Job is processed
    assert task.status == TaskStatus.COMPLETED
    assert task.name == "test"
    assert task.value == 1
