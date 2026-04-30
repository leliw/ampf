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

## Error Handling

* **`ValueError`**: Raised if a registered function lacks a return type annotation or if a requested type is not registered.
* **`TypeError`**: Raised if you attempt to use `get()` for a dependency that is defined as an asynchronous function.
* **`RuntimeError`**: Raised when a circular dependency (e.g., A depends on B, B depends on A) is detected.
