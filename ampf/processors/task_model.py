import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Type

from pydantic import BaseModel

Processor = Callable[[Any], None] | Callable[[Any], Awaitable[None]]

_log = logging.getLogger(__name__)


@dataclass
class ProcessorDefinition:
    processor: Processor
    payload_type: Type[BaseModel] | None = None


class TaskRegistry:
    _tasks: dict[str, ProcessorDefinition] = {}

    @classmethod
    def register(cls, name: str, payload_type: Type[BaseModel] | None = None):
        def decorator(processor: Processor):
            _log.debug(f"Registering processor: {name}")
            cls._tasks[name] = ProcessorDefinition(processor, payload_type)
            return processor

        return decorator


class TaskRunner(ABC):
    @abstractmethod
    def run(self, name: str, *args, **kwargs):
        pass

    @abstractmethod
    async def run_async(self, name: str, *args, **kwargs):
        pass

    @classmethod
    def create(cls) -> "TaskRunner":
        raise NotImplementedError()
