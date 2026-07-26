import asyncio
import inspect
import logging
from typing import Annotated, Any, Type, get_args, get_origin

from pydantic import BaseModel

from ampf.dependency.dependency_registry import DependencyRegistry

from .task_model import ProcessorDefinition, SyncOrAsyncCallable, TaskRunner

_log = logging.getLogger(__name__)


class TaskRegistry:
    _tasks: dict[str, ProcessorDefinition] = {}

    @classmethod
    def register(cls, processor_name: str, payload_type: Type[BaseModel] | None = None):
        def decorator(processor: SyncOrAsyncCallable):
            params = cls.get_parameters(processor)
            if not payload_type:
                for n, t in params.items():
                    if isinstance(t, type) and issubclass(t, BaseModel):
                        payload_type_param = t
            else:
                payload_type_param = payload_type
            _log.debug(f"Registering processor: {processor_name}")
            cls._tasks[processor_name] = ProcessorDefinition(processor, payload_type_param, params)
            return processor

        return decorator

    @classmethod
    def get_parameters(cls, func: SyncOrAsyncCallable) -> dict[str, Type[Any]]:
        sig = inspect.signature(func)
        params = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.annotation is inspect._empty:
                raise TypeError(f"Parameter '{name}' in {func.__name__} must have a type annotation")
            if get_origin(param.annotation) is Annotated:
                param_type = get_args(param.annotation)[0]
            else:
                param_type = param.annotation
            params[name] = param_type
        return params

    @classmethod
    def get_task_parameters(cls, task_runner: TaskRunner, name: str, payload: BaseModel) -> dict[str, Any]:
        with DependencyRegistry.scope() as local_registry:
            local_registry.add(task_runner, TaskRunner)
            parameters = {}
            for param_name, param_type in cls._tasks[name].params.items():
                actual_type = get_origin(param_type) or param_type
                if isinstance(payload, actual_type):
                    parameters[param_name] = payload
                else:
                    parameters[param_name] = local_registry.get(param_type)
            return parameters

    @classmethod
    def run_task(cls, task_runner: TaskRunner, name: str, payload: BaseModel) -> None:
        processor = cls._tasks[name].processor
        parameters = cls.get_task_parameters(task_runner, name, payload)
        if callable(processor):
            if inspect.iscoroutinefunction(processor):
                raise TypeError(
                    f"Processor '{name}' is an asynchronous task. Use 'run_async' for asynchronous execution."
                )
            processor(**parameters)
        else:
            raise ValueError(f"Processor {name} is not callable")

    @classmethod
    async def run_task_async(cls, task_runner: TaskRunner, name: str, payload: BaseModel) -> None:
        processor = cls._tasks[name].processor
        parameters = cls.get_task_parameters(task_runner, name, payload)
        if callable(processor):
            ret = processor(**parameters)
            if asyncio.iscoroutine(ret):
                await ret
        else:
            raise ValueError(f"Processor {name} is not callable")
