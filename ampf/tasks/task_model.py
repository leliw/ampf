import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

type SyncOrAsyncCallable[T] = Callable[..., T] | Callable[..., Awaitable[T]]


_log = logging.getLogger(__name__)


@dataclass
class ProcessorDefinition:
    processor: SyncOrAsyncCallable
    payload_type: type[BaseModel] | None = None
    params: dict[str, type[Any]] = field(default_factory=dict)


class TaskRunner(ABC):
    @abstractmethod
    def run(self, name: str, payload: BaseModel):
        pass

    @abstractmethod
    async def run_async(self, name: str, payload: BaseModel):
        pass

    @classmethod
    def create(cls, *args, **kwargs) -> "TaskRunner":
        raise NotImplementedError()


class ManagedTaskRunner(TaskRunner):
    @asynccontextmanager
    async def manage_lifecycle(self, app: FastAPI):
        yield self
