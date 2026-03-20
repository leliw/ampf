from abc import ABC, abstractmethod
import logging
from typing import Any, Awaitable, Callable

Processor = Callable[[Any], None] | Callable[[Any], Awaitable[None]]

_log = logging.getLogger(__name__)


class TaskRegistry:
    _tasks: dict[str, Processor] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(processor: Processor):
            _log.debug(f"Registering processor: {name}")
            cls._tasks[name] = processor
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
