# Task Processing System

This document outlines the task processing system, which centralizes task management, offering flexible execution strategies. The core components are the `TaskRunner` interface and the `TaskRegistry`.

## TaskRunner Interface

The `TaskRunner` is an abstract base class that defines the contract for executing tasks.

### Methods

* `run(self, name: str, payload: BaseModel)`: Synchronously executes a task identified by `name` with the given `payload`.
* `run_async(self, name: str, payload: BaseModel)`: Asynchronously executes a task identified by `name` with the given `payload`.
* `create(cls) -> "TaskRunner"`: A class method for creating an instance of the task runner.

## TaskRegistry

The `TaskRegistry` is a central component responsible for registering and managing task processors and their dependencies. It provides mechanisms for automatic parameter and payload type detection, as well as dependency injection.

### Decorators

* `@TaskRegistry.register(processor_name: str, payload_type: Type[BaseModel] | None = None)`:
    Registers a function as a task processor. It automatically detects the `payload_type` if a `BaseModel` is used as a parameter in the processor function's signature.

    Example:

    ```python
    class MyPayload(BaseModel):
        value: int

    @TaskRegistry.register("my_task")
    async def my_processor(payload: MyPayload, dependency_a: DependencyA):
        # ... process task ...
        pass
    ```

### Dependency Injection

The `TaskRegistry` automatically resolves and injects dependencies into registered task processors using `DependencyRegistry`.

## TaskRunner Implementations

### DirectRunner

The `DirectRunner` executes tasks immediately in the current thread. It is suitable for synchronous operations or when immediate, blocking execution is desired.

Example:

```python
from ampf.processors.direct_runner import DirectRunner
from pydantic import BaseModel

class MyPayload(BaseModel):
    message: str

@TaskRegistry.register("simple_task")
def simple_processor(payload: MyPayload):
    print(f"Processing: {payload.message}")

runner = DirectRunner.create()
runner.run("simple_task", MyPayload(message="Hello World"))
```

### BackgroundRunner

The `BackgroundRunner` integrates with FastAPI's `BackgroundTasks` to run tasks in the background, allowing the API endpoint to return a response without waiting for the task to complete.

Example:

```python
from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel
from ampf.processors.background_runner import BackgroundRunner

class TaskCreate(BaseModel):
    name: str

app = FastAPI()

@TaskRegistry.register("background_processor")
async def background_processor(payload: TaskCreate):
    await asyncio.sleep(1) # Simulate async work
    print(f"Background task processed: {payload.name}")

@app.post("/api/tasks")
async def create_task(
    data: TaskCreate,
    background_tasks: BackgroundTasks,
    task_runner: Annotated[BackgroundRunner, Depends(BackgroundRunner.create)]
):
    task_runner.background_tasks = background_tasks # Inject BackgroundTasks
    await task_runner.run_async("background_processor", data)
    return {"message": "Task initiated in background"}
```

### PubsubPullRunner

The `PubsubPullRunner` enables asynchronous task processing using Google Cloud Pub/Sub. It acts as an asynchronous context manager to manage Pub/Sub subscriptions.

Example:

```python
import asyncio
from pydantic import BaseModel
from ampf.gcp import GcpAsyncFactory
from ampf.processors.pubsub_pull_runner import PubsubPullRunner

class PubsubConfig(BaseModel):
    my_pubsub_task_topic: str = "my-pubsub-topic"
    my_pubsub_task_subscription: str = "my-pubsub-subscription"

class MyPubsubPayload(BaseModel):
    data: str

@TaskRegistry.register("my_pubsub_task", MyPubsubPayload)
async def my_pubsub_processor(payload: MyPubsubPayload):
    print(f"Received Pub/Sub message: {payload.data}")
    await asyncio.sleep(1)
    print(f"Finished processing Pub/Sub message: {payload.data}")

async def main():
    gcp_factory = GcpAsyncFactory()
    config = PubsubConfig()

    async with PubsubPullRunner.create(gcp_factory, config) as runner:
        # Publish a message
        await runner.run_async("my_pubsub_task", MyPubsubPayload(data="Test message from Pub/Sub"))
        print("Message published to Pub/Sub.")
        # Allow some time for the message to be pulled and processed
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
```
