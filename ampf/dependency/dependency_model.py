from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Type


type SyncOrAsyncCallable[T] = Callable[..., T] | Callable[..., Awaitable[T]]


@dataclass
class DependencyDefinition[T]:
    callable: SyncOrAsyncCallable[T]
    params: dict[str, Type[Any]] = field(default_factory=dict)
