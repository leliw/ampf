# Task Processing System

The Task Processing System provides a centralized, flexible architecture for managing and executing background tasks. It supports multiple execution strategies—ranging from synchronous execution to Google Cloud Pub/Sub—through a unified `TaskRunner` interface, allowing developers to switch execution contexts without altering business logic.

## Key Features

* **Unified Execution Interface:** Seamlessly switch between direct execution, FastAPI background tasks, and GCP Pub/Sub (Pull/Push).
* **Dependency Injection:** Automatically resolves and injects dependencies (e.g., database sessions, storage) into task processors via `DependencyRegistry`.
* **Lifecycle Management:** Built-in support for managing the lifecycle of complex runners (like Pub/Sub subscriptions) using FastAPI's lifespan events.
* **Type Safety & Validation:** Leverages Pydantic models (`BaseTask`) for robust task payload validation and state management.

## Installation/Integration

To integrate the task processing system into your project, import the necessary components from the `ampf.tasks` module. Ensure you have `fastapi` and `pydantic` installed. If you plan to use Pub/Sub runners, the Google Cloud Pub/Sub SDK is required.

## How-To: Implement Background Tasks

This section provides a complete, step-by-step guide on how to configure the application, set up dependencies, define tasks, and expose them via FastAPI endpoints.

### 1. Define the Task Model

Create a task model by inheriting from `BaseTask`. You must implement the `result_id` property to uniquely identify the result once the task completes.

```python
from uuid import uuid4
from pydantic import BaseModel, computed_field
from ampf.tasks import BaseTask, TaskStatus

class TaskCreate(BaseModel):
    name: str | None = None
    value: int | None = None

class Task(BaseTask):
    value: int | None = None

    @computed_field
    @property
    def result_id(self) -> str | None:
        return str(self.id) if self.status == TaskStatus.COMPLETED else None

    @classmethod
    def create(cls, value_create: TaskCreate) -> "Task":
        return Task(id=uuid4(), **value_create.model_dump())
```

### 2. Register the Task Processor

Use the `@TaskRegistry.register` decorator to define the function that will process the task. Dependencies, such as `BaseAsyncStorage`, are automatically injected by the framework.

```python
import asyncio
from ampf.tasks import TaskRegistry, TaskStatus
from ampf.base.base_async_storage import BaseAsyncStorage

@TaskRegistry.register("processor", Task)
async def processor(storage: BaseAsyncStorage[Task], payload: Task) -> None:
    payload.status = TaskStatus.RUNNING
    await asyncio.sleep(1) # Simulate background work
    
    payload.value = (payload.value or 0) + 1
    payload.status = TaskStatus.COMPLETED
    await storage.save(payload)
```

### 3. Configure Application State (`AppConfig` & `AppState`)

Create configuration models to determine which runner to use and manage the initialization of required factories (e.g., GCP vs. In-Memory).

```python
from typing import Literal, Type
from functools import cached_property
from dataclasses import dataclass
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI

from ampf.base import BaseAsyncFactory
from ampf.gcp import GcpAsyncFactory
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from ampf.tasks import TaskRunner, ManagedTaskRunner, PubsubRunner
from ampf.tasks.direct_runner import DirectRunner
from ampf.tasks.background_runner import BackgroundRunner
from ampf.tasks.pubsub_pull_runner import PubsubPullRunner
from ampf.tasks.pubsub_push_runner import PubsubPushRunner

class AppConfig(BaseModel):
    task_runner: Literal["Direct", "Background", "PubsubPull", "PubsubPush"]
    processor_topic: str = "processor"
    processor_subscription: str = "processor-sub"

    @cached_property
    def task_runner_type(self) -> Type[TaskRunner]:
        match self.task_runner:
            case "Direct": return DirectRunner
            case "Background": return BackgroundRunner
            case "PubsubPush": return PubsubPushRunner
            case "PubsubPull": return PubsubPullRunner
            case _: raise ValueError(f"Unknown task runner type: {self.task_runner}")

@dataclass
class AppState:
    config: AppConfig
    factory: BaseAsyncFactory
    task_runner: TaskRunner | Type[TaskRunner]

    @classmethod
    def create(cls, config: AppConfig):
        # Initialize GCP factory for Pub/Sub, otherwise use In-Memory
        if issubclass(config.task_runner_type, PubsubRunner):
            factory = GcpAsyncFactory() 
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
```

### 4. Setup FastAPI Lifespan and Dependencies (`TaskRunnerDep`)

Configure the FastAPI lifespan to manage the `AppState` and register dependencies so they can be injected into your endpoints.

```python
from typing import Annotated
from fastapi import Depends, BackgroundTasks
from ampf.dependency.dependency_registry import DependencyRegistry, get_dependency

def lifespan(app_config: AppConfig):
    app_state = AppState.create(app_config)
    DependencyRegistry.add(app_state)
    DependencyRegistry.add(app_state.task_runner, TaskRunner)

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        app.state.app_state = app_state
        async with app_state.manage_lifecycle(app):
            yield

    return _lifespan

# Define FastAPI Dependencies
AppStateDep = Annotated[AppState, Depends(get_dependency(AppState))]
StorageTaskDep = Annotated[BaseAsyncStorage[Task], Depends(get_dependency(BaseAsyncStorage[Task]))]

# Dynamic TaskRunner Dependency
def get_task_runner(app_state: AppStateDep, background_tasks: BackgroundTasks) -> TaskRunner:
    if isinstance(app_state.task_runner, ManagedTaskRunner):
        return app_state.task_runner
    elif app_state.task_runner == BackgroundRunner:
        # BackgroundRunner requires FastAPI's BackgroundTasks object
        return BackgroundRunner(background_tasks)
    else:
        return app_state.task_runner.create()

TaskRunnerDep = Annotated[TaskRunner, Depends(get_task_runner)]
```

### 5. Create API Endpoints

Finally, create the FastAPI application and define the endpoints. Use the `TaskRunnerDep` to trigger the background task upon creation.

```python
from uuid import UUID

app = FastAPI(lifespan=lifespan(app_config))

@app.post("/api/jobs", status_code=201)
async def create_job(storage: StorageTaskDep, data: TaskCreate, task_runner: TaskRunnerDep) -> Task:
    task = Task.create(data)
    await storage.create(task)
    
    # Trigger the task registered under the name "processor"
    await task_runner.run_async("processor", task) 
    
    return task

@app.get("/api/jobs/{id}")
async def get_job(storage: StorageTaskDep, id: UUID) -> Task:
    job = await storage.get(id)
    return job
```

## API Reference

### Classes & Interfaces

| Class | Description |
| :--- | :--- |
| `TaskRunner` | Abstract base class defining the contract for executing tasks. |
| `ManagedTaskRunner` | Subclass of `TaskRunner` for runners requiring lifecycle management (e.g., Pub/Sub). |
| `TaskRegistry` | Central registry responsible for mapping task names to processor functions. |
| `BaseTask` | Base Pydantic model for tasks. Includes built-in `id` and `status` fields. |
| `TaskStatus` | Enum representing the state of a task (e.g., `PENDING`, `RUNNING`, `COMPLETED`). |

### Task Runners

| Runner | Description |
| :--- | :--- |
| `DirectRunner` | Executes tasks immediately in the current thread. Blocks the caller until completion. |
| `BackgroundRunner` | Integrates with FastAPI's `BackgroundTasks` for non-blocking, in-memory execution. |
| `PubsubPullRunner` | Asynchronously processes tasks using Google Cloud Pub/Sub pull subscriptions. |
| `PubsubPushRunner` | Processes tasks using Google Cloud Pub/Sub push endpoints. |

### Key Methods

* **`TaskRunner.run_async(name: str, payload: BaseModel) -> None`**
  * *Description:* Asynchronously executes a task identified by `name`.
  * *Parameters:*
    * `name` (str): The registered name of the task processor.
    * `payload` (BaseModel): The data payload to be processed.
* **`TaskRunner.run(name: str, payload: BaseModel) -> None`**
  * *Description:* Synchronously executes a task.
* **`ManagedTaskRunner.manage_lifecycle(app: FastAPI) -> AsyncContextManager`**
  * *Description:* Async context manager to handle startup and shutdown events for the runner.
* **`TaskRegistry.register(processor_name: str, payload_type: Type[BaseModel] | None = None)`**
  * *Description:* Decorator to register a function as a task processor.

## Error Handling

Task processors are responsible for handling their own internal business logic exceptions. If a processor encounters an error, it should catch the exception, update the task's status to a failed state (e.g., `TaskStatus.FAILED`), and persist the state to storage.

Uncaught exceptions behavior depends on the runner:

* `DirectRunner`: Exceptions propagate immediately to the caller.
* `BackgroundRunner`: Exceptions are logged by FastAPI's background task manager.
* `PubsubRunner`: Unacknowledged messages will be retried by GCP Pub/Sub based on the topic/subscription configuration (e.g., dead-letter queues).

## Testing

The provided unit tests (`tests/tasks/test_all_task_runners.py`) demonstrate how to test all runner implementations using parameterized fixtures.

**Test Coverage:**

* End-to-end task creation and background processing.
* State transitions (`PENDING` -> `RUNNING` -> `COMPLETED`).
* Compatibility across all runner types (`Direct`, `Background`, `PubsubPull`, `PubsubPush`).

**Testing Pub/Sub Push Runners:**

Testing `PubsubPushRunner` requires simulating GCP push requests. The `ApiTestClient` provides a `run_push_emulator` context manager to mock this behavior:

```python
# Example from tests/tasks/test_all_task_runners.py
if isinstance(task_runner, PubsubPushRunner):
    topic = task_runner.get_topic("processor")
    subscription = topic.create_subscription(exist_ok=True)
    
    # Run the push emulator against the test client
    with subscription.run_push_emulator(client, "/pub-sub/task-processors/processor"):
        yield client
```
