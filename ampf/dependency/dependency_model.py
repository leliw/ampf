from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

type SyncOrAsyncCallable[T] = Callable[..., T] | Callable[..., Awaitable[T]]


@dataclass
class DependencyDefinition[T]:
    callable: SyncOrAsyncCallable[T]
    params: dict[str, type[Any]] = field(default_factory=dict)
