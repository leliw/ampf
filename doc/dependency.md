# Dependency Registry Documentation

## Overview

The `DependencyRegistry` is a central component of the AMPF framework designed to manage and resolve object dependencies. It supports both synchronous and asynchronous dependency injection, allowing for clean, decoupled code by automatically resolving complex object graphs.

## Key Features

* **Type-Safe Registration:** Register providers using return type hints or explicit type mapping.
* **Sync & Async Support:** Seamlessly resolve dependencies whether they are created synchronously or via `async` functions.
* **Automatic Dependency Resolution:** Automatically injects required dependencies into provider functions.
* **Singleton Pattern:** Once a dependency is resolved, the instance is cached and reused for subsequent requests.
* **Cycle Detection:** Prevents infinite recursion by detecting circular dependencies during resolution.
* **Bulk Registration:** Easily register complex application states and their nested dataclass fields.

## Installation

The `DependencyRegistry` is part of the `ampf` library. Ensure your project has `ampf` installed in your environment.

```bash
pip install ampf
```

## Usage Examples

### 1. Basic Registration and Resolution

Register a provider function and retrieve the dependency.

```python
from ampf.dependency import DependencyRegistry

class Database:
    pass

# Register using the return type hint
@DependencyRegistry.register
def get_db() -> Database:
    return Database()

# Retrieve the dependency
db = DependencyRegistry.get(Database)
```

### 2. Handling Dependencies with Parameters

The registry automatically resolves parameters required by your provider functions.

```python
class Config:
    pass

class Service:
    def __init__(self, config: Config):
        self.config = config

@DependencyRegistry.register
def get_config() -> Config:
    return Config()

@DependencyRegistry.register
def get_service(config: Config) -> Service:
    return Service(config)

# Automatically resolves Config before creating Service
service = DependencyRegistry.get(Service)
```

### 3. Asynchronous Dependencies

For I/O-bound operations, use `get_async`.

```python
@DependencyRegistry.register
async def get_async_data() -> str:
    return "data"

# In an async context:
data = await DependencyRegistry.get_async(str)
```

### 4. Class Registration

You can also register a class directly. The registry will inspect its `__init__` method to resolve dependencies.

```python
class Database:
    pass

@DependencyRegistry.register_class
class MyService:
    def __init__(self, db: Database):
        self.db = db

@DependencyRegistry.register
def get_db() -> Database:
    return Database()

# Retrieve the dependency
service = DependencyRegistry.get(MyService)
```

### 5. Optional Dependencies

The registry supports `Optional` dependencies (e.g., `Optional[MyService]` or `MyService | None`). If an optional dependency is not registered, the registry will inject `None` instead of raising an error.

```python
from typing import Optional

class Logger:
    pass

class Service:
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger

@DependencyRegistry.register
def get_service(logger: Optional[Logger]) -> Service:
    # logger will be None if Logger is not registered
    return Service(logger)
```

*Note: Complex Union types (e.g., `Union[ServiceA, ServiceB, None]`) are not supported and will raise a `TypeError`.*

### 6. Integration with FastAPI (`get_dependency`)

The `get_dependency` helper function creates a callable that retrieves a specific dependency from the registry. This is particularly useful for integrating with frameworks like FastAPI using `Depends`.

```python
from fastapi import APIRouter, Depends
from ampf.dependency import get_dependency

router = APIRouter()

@router.get("/items")
def read_items(service: MyService = Depends(get_dependency(MyService))):
    return service.get_items()
```

## API Reference

### `DependencyRegistry`

The main class for managing dependencies. All methods are `@classmethod`.

| Method | Description |
| :--- | :--- |
| `register(fn)` | Decorator: Registers a function based on its return type hint. |
| `register_for_type(type)(fn)` | Decorator: Registers a function as a provider for a specific type. |
| `register_class(cls)` | Decorator: Registers a class as a dependency provider. |
| `get(type)` | Synchronously retrieves an instance of the requested type. |
| `get_async(type)` | Asynchronously retrieves an instance of the requested type. |
| `add(obj, type=None)` | Manually adds an existing instance to the registry. |
| `add_all(obj)` | Adds an object and its dataclass fields to the registry. |
| `clear()` | Clears all registered dependencies and cached instances. |

### Helper Functions

| Function | Description |
| :--- | :--- |
| `get_dependency(clazz)` | Returns a callable that retrieves the specified dependency type from the registry. Ideal for use with FastAPI's `Depends`. |

## Error Handling

* **`ValueError`**: Raised if a registered function lacks a return type annotation or if a requested type is not registered.
* **`TypeError`**: Raised if you attempt to use `get()` for a dependency that is defined as an asynchronous function, or if a complex `Union` type is used for a dependency.
* **`RuntimeError`**: Raised when a circular dependency (e.g., A depends on B, B depends on A) is detected.
