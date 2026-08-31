import asyncio
import inspect
import logging
from typing import Annotated, Any, ClassVar, get_args, get_origin

from pydantic import BaseModel

from ampf.dependency.dependency_registry import DependencyRegistry

from .task_model import ProcessorDefinition, SyncOrAsyncCallable, TaskRunner

_log = logging.getLogger(__name__)


class TaskRegistry:
    _tasks: ClassVar[dict[str, ProcessorDefinition]] = {}

    @classmethod
    def clear_tasks(cls) -> None:
        cls._tasks.clear()

    @classmethod
    def register(cls, processor_name: str, payload_type: type[BaseModel] | None = None, external: bool = False):
        def decorator(processor: SyncOrAsyncCallable):
            params = cls.get_parameters(processor)
            if not payload_type:
                payload_type_param: type[BaseModel] | None = None 
                for t in params.values():
                    if isinstance(t, type) and not get_origin(t) and issubclass(t, BaseModel):
                        payload_type_param = t
                        break
            else:
                payload_type_param = payload_type
            _log.debug("Registering processor: %s", processor_name)
            cls._tasks[processor_name] = ProcessorDefinition(processor, payload_type_param, params, external)
            return processor

        return decorator

    @classmethod
    def get_parameters(cls, func: SyncOrAsyncCallable) -> dict[str, type[Any]]:
        sig = inspect.signature(func)
        params = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.annotation is inspect.Parameter.empty:
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
                    f"Processor '{name}' is an asynchronous task. Use 'run_task_async' for asynchronous execution."
                )
            processor(**parameters)
        else:
            raise TypeError(f"Processor {name} is not callable")

    @classmethod
    async def run_task_async(cls, task_runner: TaskRunner, name: str, payload: BaseModel) -> None:
        processor = cls._tasks[name].processor
        parameters = cls.get_task_parameters(task_runner, name, payload)
        if callable(processor):
            ret = processor(**parameters)
            if asyncio.iscoroutine(ret):
                await ret
        else:
            raise TypeError(f"Processor {name} is not callable")
