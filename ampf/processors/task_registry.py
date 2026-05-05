import asyncio
import inspect
import logging
from typing import Annotated, Any, Type, get_args, get_origin

from pydantic import BaseModel

from ampf.dependency.dependency_registry import DependencyRegistry
from ampf.processors.task_model import ProcessorDefinition, SyncOrAsyncCallable

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
    def get_parameters(cls, callable: SyncOrAsyncCallable) -> dict[str, Type[Any]]:
        sig = inspect.signature(callable)
        params = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.annotation is inspect._empty:
                raise TypeError(f"Parameter '{name}' in {cls}.__init__ must have a type annotation")
            if get_origin(param.annotation) is Annotated:
                param_type = get_args(param.annotation)[0]
            else:
                param_type = param.annotation
            params[name] = param_type
        return params

    @classmethod
    def get_dependency[T](cls, dependency_type: Type[T]) -> T:
        """
        Retrieves an instance of a registered dependency.

        Args:
            dependency_type: The type of the dependency to retrieve.

        Returns:
            An instance of the requested dependency.

        Raises:
            ValueError: If the dependency type is not registered.
        """
        return DependencyRegistry.get(dependency_type)

    @classmethod
    def get_task_parameters(cls, name: str, payload: BaseModel) -> dict[str, Any]:
        parameters = {}
        for param_name, param_type in cls._tasks[name].params.items():
            if payload.__class__ == param_type:
                parameters[param_name] = payload
            else:
                parameters[param_name] = cls.get_dependency(param_type)
        return parameters

    @classmethod
    def get_call_parameters(cls, params: dict[str, Type[Any]], payload: BaseModel | None = None) -> dict[str, Any]:
        parameters = {}
        for param_name, param_type in params.items():
            # if get_origin(param_type) is Annotated:
            #     param_type = get_args(param_type)[0]
            if payload and payload.__class__ == param_type:
                parameters[param_name] = payload
            else:
                parameters[param_name] = cls.get_dependency(param_type)
        return parameters

    @classmethod
    def run_task(cls, name: str, payload: BaseModel) -> None:
        processor = cls._tasks[name].processor
        parameters = cls.get_task_parameters(name, payload)
        if callable(processor):
            ret = processor(**parameters)
            if asyncio.iscoroutine(ret):
                raise TypeError(
                    f"Processor '{name}' is an asynchronous task. Use 'run_async' for asynchronous execution."
                )
        else:
            raise ValueError(f"Processor {name} is not callable")

    @classmethod
    async def run_task_async(cls, name: str, payload: BaseModel) -> None:
        processor = cls._tasks[name].processor
        parameters = cls.get_task_parameters(name, payload)
        if callable(processor):
            ret = processor(**parameters)
            if asyncio.iscoroutine(ret):
                await ret
        else:
            raise ValueError(f"Processor {name} is not callable")
