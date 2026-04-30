import inspect
import logging
from dataclasses import fields, is_dataclass
import types
from typing import Annotated, Any, Callable, Protocol, Type, get_args, get_origin, get_type_hints
import typing

from pydantic import BaseModel

from .dependency_model import DependencyDefinition, SyncOrAsyncCallable

_log = logging.getLogger(__name__)


class DependencyRegistry:
    """
    A registry for managing and resolving synchronous and asynchronous dependencies.
    """

    _dependencies: dict[Type[Any], DependencyDefinition] = {}
    _objects: dict[Type[Any], Any] = {}

    @classmethod
    def clear(cls) -> None:
        """
        Clears all registered dependencies and cached object instances.
        """
        cls._dependencies = {}
        cls._objects = {}

    @classmethod
    def add(cls, instance: Any, instance_type: Type[Any] | None = None) -> None:
        """
        Manually adds an object instance to the registry.

        Args:
            instance: The instance to add.
            instance_type: Optional type to register the object under. Defaults to object.__class__.
        """
        cls._objects[instance_type or instance.__class__] = instance
        _log.debug("Added object to registry: %s", instance_type or instance.__class__)

    @classmethod
    def add_all(cls, instance: Any) -> None:
        """
        Adds an object and its dataclass fields to the registry if they are not built-in types.

        Args:
            instance: The object whose fields should be registered.
        """
        cls._objects[instance.__class__] = instance
        if is_dataclass(instance) and not isinstance(instance, type):
            for field in fields(instance):
                declared_type = field.type
                value = getattr(instance, field.name)
                if (
                    declared_type.__module__ != "builtins"
                    and not isinstance(value, type)
                    and isinstance(declared_type, type)
                ):
                    cls.add(value, declared_type)

    @classmethod
    def register[T](cls, fn: SyncOrAsyncCallable[T]) -> SyncOrAsyncCallable[T]:
        """
        Decorator to register a function as a dependency provider based on its return type hint.

        Args:
            fn: The callable that provides the dependency.

        Returns:
            The original callable.

        Raises:
            ValueError: If the function lacks a return type annotation.
        """
        dependency_type = get_type_hints(fn).get("return")

        if dependency_type is None or dependency_type is inspect.Parameter.empty:
            raise ValueError(f"Function {fn.__name__} must have return type annotation")
        params = cls.get_parameters(fn)
        cls._dependencies[dependency_type] = DependencyDefinition(fn, params)
        return fn

    @classmethod
    def register_for_type[T](
        cls, dependency_type: Type[T]
    ) -> Callable[[SyncOrAsyncCallable[T]], SyncOrAsyncCallable[T]]:
        """
        Decorator to register a function as a provider for a specific type.

        Args:
            dependency_type: The type this provider satisfies.

        Returns:
            A decorator function.
        """

        def decorator(fn: SyncOrAsyncCallable[T]) -> SyncOrAsyncCallable[T]:
            params = cls.get_parameters(fn)
            cls._dependencies[dependency_type] = DependencyDefinition(fn, params)
            return fn

        return decorator

    @classmethod
    def register_class[T](cls, dependency_class: Type[T]) -> Type[T]:
        """
        Decorator to register a class as a dependency provider.

        Args:
            dependency_class: The class to register.

        Returns:
            The original class.
        """
        params = cls.get_parameters(dependency_class)
        cls._dependencies[dependency_class] = DependencyDefinition(dependency_class, params)
        return dependency_class

    @classmethod
    def get_parameters(cls, func: SyncOrAsyncCallable) -> dict[str, Type[Any]]:
        """
        Inspects a callable to extract its parameter names and types.

        Args:
            func: The function to inspect.

        Returns:
            A dictionary mapping parameter names to their types.

        Raises:
            TypeError: If a parameter lacks a type annotation.
        """
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
    def get[T](cls, dependency_type: Type[T], stack: set[Type] | None = None) -> T:
        """
        Synchronously retrieves or creates an instance of a registered dependency.

        Args:
            dependency_type: The type of the dependency to retrieve.
            stack: Internal set to track recursion and detect cycles.

        Returns:
            An instance of the requested dependency.

        Raises:
            RuntimeError: If a circular dependency is detected.
            ValueError: If the dependency type is not registered.
            TypeError: If the dependency provider is asynchronous.
        """
        if dependency_type in cls._objects:
            return cls._objects[dependency_type]
        stack = stack or set()
        if dependency_type in stack:
            raise RuntimeError(f"Cycle detected: {dependency_type}")
        stack.add(dependency_type)
        if dependency_type not in cls._dependencies:
            raise ValueError(f"Dependency of type {dependency_type} is not registered in DependencyRegistry.")
        parameters = cls.get_call_parameters(cls._dependencies[dependency_type].params, stack)
        ret = cls._dependencies[dependency_type].callable(**parameters)
        if inspect.isawaitable(ret):
            raise TypeError(
                f"Dependency '{dependency_type}' is asynchronous. Use 'get_async' for asynchronous execution."
            )
        cls._objects[dependency_type] = ret
        return ret

    @classmethod
    async def get_async[T](cls, dependency_type: Type[T], stack: set[Type] | None = None) -> T:
        """
        Asynchronously retrieves or creates an instance of a registered dependency.

        Args:
            dependency_type: The type of the dependency to retrieve.
            stack: Internal set to track recursion and detect cycles.

        Returns:
            An instance of the requested dependency.

        Raises:
            RuntimeError: If a circular dependency is detected.
            ValueError: If the dependency type is not registered.
        """
        if dependency_type in cls._objects:
            return cls._objects[dependency_type]
        stack = stack or set()
        if dependency_type in stack:
            raise RuntimeError(f"Cycle detected: {dependency_type}")
        stack.add(dependency_type)
        if dependency_type not in cls._dependencies:
            raise ValueError(f"Dependency of type {dependency_type} is not registered in DependencyRegistry.")
        parameters = await cls.get_call_parameters_async(cls._dependencies[dependency_type].params, stack)
        ret = cls._dependencies[dependency_type].callable(**parameters)
        if inspect.isawaitable(ret):
            ret = await ret
        cls._objects[dependency_type] = ret
        return ret

    @classmethod
    def get_call_parameters(
        cls, params: dict[str, Type[Any]], stack: set[Type], payload: BaseModel | None = None
    ) -> dict[str, Any]:
        """
        Resolves a dictionary of parameter types into their corresponding instances synchronously.

        Args:
            params: Dictionary of parameter names and types.
            stack: Current resolution stack for cycle detection.
            payload: Optional Pydantic model to use for parameter resolution (currently unused).

        Returns:
            A dictionary of parameter names and resolved instances.
        """
        parameters = {}
        for param_name, param_type in params.items():
            origin = typing.get_origin(param_type)
            args = typing.get_args(param_type)
            is_optional = False
            actual_type = param_type

            if origin is typing.Union or (hasattr(types, "UnionType") and origin is types.UnionType):
                if type(None) in args:
                    is_optional = True
                    non_none_args = [arg for arg in args if arg is not type(None)]
                    if len(non_none_args) > 1:
                        raise TypeError(f"Complex Union types are not supported for dependency injection: {param_type}")
                    actual_type = non_none_args[0]
            try:
                parameters[param_name] = cls.get(actual_type, stack)
            except ValueError:
                if is_optional:
                    parameters[param_name] = None
                    if actual_type in stack:
                        stack.remove(actual_type)
                else:
                    raise
        return parameters

    @classmethod
    async def get_call_parameters_async(
        cls,
        params: dict[str, Type[Any]],
        stack: set[Type],
        payload: BaseModel | None = None,
    ) -> dict[str, Any]:
        """
        Resolves a dictionary of parameter types into their corresponding instances asynchronously.

        Args:
            params: Dictionary of parameter names and types.
            stack: Current resolution stack for cycle detection.
            payload: Optional Pydantic model to use for parameter resolution (currently unused).

        Returns:
            A dictionary of parameter names and resolved instances.
        """
        parameters = {}
        for param_name, param_type in params.items():
            origin = typing.get_origin(param_type)
            args = typing.get_args(param_type)
            is_optional = False
            actual_type = param_type

            if origin is typing.Union or (hasattr(types, "UnionType") and origin is types.UnionType):
                if type(None) in args:
                    is_optional = True
                    non_none_args = [arg for arg in args if arg is not type(None)]
                    if len(non_none_args) > 1:
                        raise TypeError(f"Complex Union types are not supported for dependency injection: {param_type}")
                    actual_type = non_none_args[0]
            try:
                parameters[param_name] = await cls.get_async(actual_type, stack)
            except ValueError:
                if is_optional:
                    parameters[param_name] = None
                    if actual_type in stack:
                        stack.remove(actual_type)
                else:
                    raise
        return parameters

class GetDependency[T](Protocol):
    def __call__(self, dependency_registry: DependencyRegistry | None = None) -> T:
        ...


def get_dependency[T](clazz: Type[T]) -> GetDependency[T]:
    """Returns a function that retrieves a dependency of the specified type from the DependencyRegistry.

    Args:
        clazz (Type[T]): The type of the dependency to retrieve.

    Returns:
        Callable[[DependencyRegistry | None], T]: A function that retrieves the dependency.
    """

    def ret_dep(dependency_registry: DependencyRegistry | None = None) -> T:
        if dependency_registry:
            return dependency_registry.get(clazz)
        else:
            return DependencyRegistry.get(clazz)

    return ret_dep
