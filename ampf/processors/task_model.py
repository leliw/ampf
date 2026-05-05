import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Type

from pydantic import BaseModel

type SyncOrAsyncCallable[T] = Callable[..., T] | Callable[..., Awaitable[T]]


_log = logging.getLogger(__name__)


@dataclass
class ProcessorDefinition:
    processor: SyncOrAsyncCallable
    payload_type: Type[BaseModel] | None = None
    params: dict[str, Type[Any]] = field(default_factory=dict)



class TaskRunner(ABC):
    @abstractmethod
    def run(self, name: str, payload: BaseModel):
        pass

    @abstractmethod
    async def run_async(self, name: str, payload: BaseModel):
        pass

    @classmethod
    def create(cls) -> "TaskRunner":
        raise NotImplementedError()
