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
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest
from ampf.gcp.gcp_subscription_pull import GcpSubscriptionPull
from ampf.tasks import BaseTask, TaskRegistry, TaskRunner, TaskStatus
from ampf.tasks.pubsub_push_runner import PubsubPushRunner
from ampf.tasks.tasks_app import TasksAppState, get_dependency_container
from ampf.testing import ApiTestClient

### Models ###


class MyTaskCreate(BaseModel):
    name: str | None = None
    value: int | None = None


class MyTask(BaseTask):
    value: int | None = None

    @classmethod
    def create(cls, value_create: MyTaskCreate) -> "MyTask":
        return MyTask(id=uuid4(), **value_create.model_dump())


### Application & dependencies ###


# AppConfig has properties:
# * task_runner - which runner is used (as string)
# * requests_topic, responses_topic and responses_subscription - for PubsubPullRunner - which topics and subscription are used.
#   The prefix `external_service` is the name of used processor (@see `@TaskRegistry.register("external_service", external=True)` below)
class AppConfig(BaseSettings):
    task_runner: Literal["Direct", "Background", "PubsubPull", "PubsubPush"]
    external_service_requests_topic: str = "it-ampf-external-service-requests"
    external_service_responses_topic: str = "it-ampf-external-service-responses"
    external_service_responses_subscription: str = "it-ampf-external-service-responses-sub"


@dataclass
class AppState(TasksAppState[AppConfig]):
    @classmethod
    def create(cls, config: AppConfig) -> Self:
        factory = GcpAsyncFactory()  # Required by PubsubRunner
        return cls(config=config, factory=factory)


def lifespan(app_config: AppConfig):
    # Clear initialized objects (for tests)
    DependencyRegistry.clear_objects()
    TaskRegistry.clear_tasks()
    app_state = AppState.create(app_config)
    DependencyRegistry.add_all(app_state)
    DependencyRegistry.add(app_state, TasksAppState)

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

    # Register external service with name "external_service"
    # Allowed parameters:
    # * Non FastApi dependencies
    # * payload inheriting Pydantic BaseModel
    @TaskRegistry.register("external_service", external=True)
    async def response_handler(storage: BaseAsyncStorage[MyTask], payload: MyTask) -> None:
        await storage.save(payload)  # Just save the response payload to storage

    @app.post("/api/tasks", status_code=201)
    async def post(dc: DependencyContainerDep, data: MyTaskCreate) -> MyTask:
        storage = dc.get(BaseAsyncStorage[MyTask])
        task_runner = dc.get(TaskRunner)
        task = MyTask.create(data)
        await storage.create(task)
        await task_runner.run_async("external_service", task)  # <--- Runs external service
        return task

    @app.get("/api/tasks/{id}")
    async def get(dc: DependencyContainerDep, id: UUID) -> MyTask:
        storage = dc.get(BaseAsyncStorage[MyTask])
        task = await storage.get(id)
        return task

    return app


@pytest.fixture(params=["Direct", "Background", "PubsubPull", "PubsubPush"])
def app_config(request: pytest.FixtureRequest) -> AppConfig:
    return AppConfig(task_runner=request.param)


@pytest.fixture
def app(app_config: AppConfig) -> FastAPI:
    return main_app(app_config)


@pytest.fixture
def client(app: FastAPI):
    with ApiTestClient(app) as client:
        app_state: AppState = app.state.app_state
        app_config = app_state.config
        if isinstance(app_state.task_runner, PubsubPushRunner):
            # PubsubPush requires extra emulator for test
            topic = app_state.factory.create_topic(app_config.external_service_responses_topic)
            processor_endpoint = "/pub-sub/task-processors/external_service"
            subscription = topic.create_subscription(exist_ok=True)
            subscription.clear()
            with subscription.run_push_emulator(client, processor_endpoint):
                yield client
        else:
            yield client


@pytest.fixture
async def external_service_mock(app: FastAPI):
    # Setup a mock for external service - it will run in background and will respond to requests from PubsubPullRunner
    # The mock will be used for Direct and Background runners, while PubsubPull and PubsubPush runners will use the real external service processor.
    app_state: AppState = app.state.app_state
    app_config = app_state.config
    if app_config.task_runner in ["Direct", "Background"]:
        # Override external service with mock
        @TaskRegistry.register("external_service", external=False)
        async def mock(storage: BaseAsyncStorage[MyTask], payload: MyTask) -> None:
            payload.value = 1
            payload.status = TaskStatus.COMPLETED
            await storage.save(payload)  # Just save the response payload to storage

        yield None
    else:
        subscription_name = f"{app_config.external_service_requests_topic}-sub"

        async def callback_async(request: GcpPubsubRequest):
            payload = request.decoded_data(MyTask)
            payload.value = 1
            payload.status = TaskStatus.COMPLETED
            await request.publish_response_async(app_state.factory, payload)
            return True

        loop = asyncio.get_running_loop()
        subscription = GcpSubscriptionPull(subscription_name, loop=loop)
        subscription.callback_async = callback_async
        subscription.run()
        try:
            yield subscription
        finally:
            subscription.stop()


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_run_task_by_endpoint(client: ApiTestClient, external_service_mock):
    # Given: An application and registered external service processor
    # When: Call POST endpoint with initial Task value
    task = client.post_typed("/api/tasks", 201, MyTask, json=MyTaskCreate(name="test"))
    # And: Wait for end of the process
    while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        await asyncio.sleep(0.1)
        task = client.get_typed(f"/api/tasks/{task.id}", 200, MyTask)
    # Then: Task is processed by external service and response is saved in storage
    assert task.status == TaskStatus.COMPLETED
    assert task.name == "test"
    assert task.value == 1
