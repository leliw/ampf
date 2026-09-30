# External Tasks Support

External Tasks enable asynchronous integration with external services and workers using Google Cloud Pub/Sub. When a task is marked as external (`external=True`), AMPF separates request publishing from response processing, routing requests to external workers and processing their responses through dedicated topics and subscriptions.

---

## Key Features

* **Decoupled Request/Response Architecture:** Dispatches task requests to external workers and listens for asynchronous responses.
* **Automatic Metadata Propagation:** Injects the response topic name into the Pub/Sub message metadata so external workers know where to send results.
* **Dependency Injection in Callbacks:** Automatically injects registered dependencies (e.g., storage, factories) into response handlers via `DependencyRegistry`.
* **Multi-Runner Support:** Supports `PubsubPullRunner`, `PubsubPushRunner`, and simplifies local development and testing with `DirectRunner` and `BackgroundRunner`.

---

## 1. Registration (`@TaskRegistry.register`)

To register a task handler for an external service, set `external=True`. The registered function acts as a **callback / response handler** that processes and persists the result returned by the external service.

Allowed parameters:

* Non-FastAPI dependencies registered in `DependencyRegistry` (e.g. `BaseAsyncStorage`).
* Payload model inheriting from Pydantic `BaseModel`.

```python
from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.tasks import TaskRegistry
from my_app.models import MyTask

# Registered response handler
@TaskRegistry.register("external_service", external=True)
async def response_handler(storage: BaseAsyncStorage[MyTask], payload: MyTask) -> None:
    """Processes and saves the response payload returned by the external worker."""
    await storage.save(payload)
```

---

## 2. Configuration Conventions

Pub/Sub runners resolve topic and subscription names dynamically from the application configuration object using the task name as a prefix:

| Property | Description |
| --- | --- |
| `{task_name}_requests_topic` | Topic where the application publishes task requests for external workers. |
| `{task_name}_responses_topic` | Topic name passed as metadata (`response_topic`) in the request message so the external worker knows where to publish the result. |
| `{task_name}_responses_subscription` | Subscription used by the application runner (e.g. `PubsubPullRunner`) to consume responses and route them to the response handler. |

### Configuration Example

```python
from typing import Literal
from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    task_runner: Literal["Direct", "Background", "PubsubPull", "PubsubPush"]
    
    # Required Pub/Sub properties for task "external_service"
    external_service_requests_topic: str = "it-ampf-external-service-requests"
    external_service_responses_topic: str = "it-ampf-external-service-responses"
    external_service_responses_subscription: str = "it-ampf-external-service-responses-sub"
```

---

## 3. Workflow & Lifecycle

```text
[ FastAPI App ] 
       │  (1) task_runner.run_async("external_service", task)
       ▼
[ {task_name}_requests_topic ] ── (includes 'response_topic' metadata)
       │
       ▼
[ External Worker / Service ] 
       │  (Processes task & publishes result to response_topic)
       ▼
[ {task_name}_responses_topic ]
       │
       ▼
[ {task_name}_responses_subscription ]
       │
       ▼
[ PubsubPullRunner / PubsubPushRunner ]
       │  (2) Executes registered response_handler(payload)
       ▼
[ Storage / Database ]
```

1. **Triggering the Task**: Calling `await task_runner.run_async("external_service", task)` retrieves `{task_name}_requests_topic` and `{task_name}_responses_topic`, then publishes the payload along with the `response_topic` attribute.
2. **External Processing**: The external worker consumes the request, performs processing, and publishes the finished payload back to the specified response topic.
3. **Receiving Response**:
   * **`PubsubPullRunner`**: Automatically starts a pull subscription listening to `{task_name}_responses_subscription` during lifespan startup and routes incoming messages to the response handler.
   * **`PubsubPushRunner`**: Exposes a push route at `/pub-sub/task-processors/{task_name}` returning status `204 No Content` and routes push requests to the response handler.

---

## 4. How-To: Complete Implementation Guide

The following example demonstrates how to set up task models, application configuration, lifespan management, dependencies, and FastAPI endpoints.

### Step 1: Define Task Models

Inherit from `BaseTask` for the main task entity and use a separate model for task creation.

```python
from uuid import uuid4
from pydantic import BaseModel
from ampf.tasks import BaseTask

class MyTaskCreate(BaseModel):
    name: str | None = None
    value: int | None = None

class MyTask(BaseTask):
    value: int | None = None

    @classmethod
    def create(cls, value_create: MyTaskCreate) -> "MyTask":
        return MyTask(id=uuid4(), **value_create.model_dump())
```

### Step 2: Configure Application State and Lifespan

Extend `TasksAppState` to manage runner lifecycles and register dependencies in `DependencyRegistry`.

```python
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal, Self
from fastapi import Depends, FastAPI
from pydantic_settings import BaseSettings

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.base_async_storage import BaseAsyncStorage
from ampf.dependency.dependency_container import DependencyContainer
from ampf.dependency.dependency_registry import DependencyRegistry
from ampf.gcp import GcpAsyncFactory
from ampf.tasks import TaskRegistry
from ampf.tasks.tasks_app import TasksAppState, get_dependency_container

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
    # Clear initialized objects (useful for tests)
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
```

### Step 3: Build the FastAPI Application

Register the response callback and expose endpoints to initiate external tasks and check their status.

```python
from uuid import UUID
from ampf.tasks import TaskRegistry, TaskRunner

def create_app(app_config: AppConfig) -> FastAPI:
    app = FastAPI(lifespan=lifespan(app_config))

    # Register external service response handler
    @TaskRegistry.register("external_service", external=True)
    async def response_handler(storage: BaseAsyncStorage[MyTask], payload: MyTask) -> None:
        await storage.save(payload)

    @app.post("/api/tasks", status_code=201)
    async def create_task(dc: DependencyContainerDep, data: MyTaskCreate) -> MyTask:
        storage = dc.get(BaseAsyncStorage[MyTask])
        task_runner = dc.get(TaskRunner)
        task = MyTask.create(data)
        await storage.create(task)
        await task_runner.run_async("external_service", task)  # Dispatches external task
        return task

    @app.get("/api/tasks/{id}")
    async def get_task(dc: DependencyContainerDep, id: UUID) -> MyTask:
        storage = dc.get(BaseAsyncStorage[MyTask])
        return await storage.get(id)

    return app
```

---

## 5. External Worker Integration Contract

External workers consume request messages from `{task_name}_requests_topic` and publish results back to the response topic specified in the request metadata.

In Python workers using AMPF:

```python
from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest
from ampf.tasks import TaskStatus

async def external_worker_handler(request: GcpPubsubRequest, factory: GcpAsyncFactory):
    # 1. Decode request data into Pydantic model
    payload = request.decoded_data(MyTask)
    
    # 2. Perform external work
    payload.value = 1
    payload.status = TaskStatus.COMPLETED
    
    # 3. Publish result to response_topic specified in request metadata
    await request.publish_response_async(factory, payload)
    return True
```

---

## 6. Testing External Tasks

The following examples demonstrate how to test all four runner modes (`Direct`, `Background`, `PubsubPull`, `PubsubPush`).

### Testing Fixtures

```python
import asyncio
import pytest
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest
from ampf.gcp.gcp_subscription_pull import GcpSubscriptionPull
from ampf.tasks import TaskRegistry, TaskStatus
from ampf.tasks.pubsub_push_runner import PubsubPushRunner
from ampf.testing import ApiTestClient

@pytest.fixture(params=["Direct", "Background", "PubsubPull", "PubsubPush"])
def app_config(request: pytest.FixtureRequest) -> AppConfig:
    return AppConfig(task_runner=request.param)

@pytest.fixture
def app(app_config: AppConfig) -> FastAPI:
    return create_app(app_config)

@pytest.fixture
def client(app: FastAPI):
    with ApiTestClient(app) as client:
        app_state: AppState = app.state.app_state
        app_config = app_state.config
        if isinstance(app_state.task_runner, PubsubPushRunner):
            # PubsubPush requires push emulator setup in tests
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
    app_state: AppState = app.state.app_state
    app_config = app_state.config

    if app_config.task_runner in ["Direct", "Background"]:
        # Override external task handler with mock for Direct & Background runners
        @TaskRegistry.register("external_service", external=False)
        async def mock_handler(storage: BaseAsyncStorage[MyTask], payload: MyTask) -> None:
            payload.value = 1
            payload.status = TaskStatus.COMPLETED
            await storage.save(payload)

        yield None
    else:
        # Mock external worker subscribing to requests topic for PubSub runners
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
```

### End-to-End Test

```python
@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_run_external_task(client: ApiTestClient, external_service_mock):
    # Trigger task creation
    task = client.post_typed("/api/tasks", 201, MyTask, json=MyTaskCreate(name="test"))
    
    # Wait for completion
    while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        await asyncio.sleep(0.1)
        task = client.get_typed(f"/api/tasks/{task.id}", 200, MyTask)
        
    # Verify result
    assert task.status == TaskStatus.COMPLETED
    assert task.name == "test"
    assert task.value == 1
```
