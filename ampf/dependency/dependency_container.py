import inspect
import types
import typing
from dataclasses import fields, is_dataclass
from typing import Annotated, Any, Callable, Type, get_args, get_origin, get_type_hints

from ampf.dependency.dependency_model import DependencyDefinition, SyncOrAsyncCallable


class DependencyContainer:
    def __init__(self, parent: "DependencyContainer | None" = None) -> None:
        self.parent = parent
        self._dependencies: dict[Type[Any], DependencyDefinition] = {}
        self._objects: dict[Type[Any], Any] = {}

    def create_scope(self) -> "DependencyContainer":
        return DependencyContainer(parent=self)

    def clear(self) -> None:
        """Clears all registered dependencies and cached object instances."""
        self._dependencies = {}
        self._objects = {}

    def clear_objects(self) -> None:
        """Clears all cached object instances."""
        self._objects = {}

    def add(self, instance: Any, instance_type: Type[Any] | None = None) -> None:
        self._objects[instance_type or instance.__class__] = instance

    def add_all(self, instance: Any) -> None:
        """Adds an object and its dataclass fields to the registry if they are not built-in types.

        Args:
            instance: The object whose fields should be registered.
        """
        self._objects[instance.__class__] = instance
        if is_dataclass(instance) and not isinstance(instance, type):
            for field in fields(instance):
                declared_type = field.type
                value = getattr(instance, field.name)
                if (
                    not isinstance(value, type)
                    and isinstance(declared_type, type)
                    and declared_type.__module__ != "builtins"
                ):
                    self.add(value, declared_type)

    def register[T](self, fn: SyncOrAsyncCallable[T]) -> SyncOrAsyncCallable[T]:
        """Decorator to register a function as a dependency provider based on its return type hint.

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
        params = self.get_parameters(fn)
        self._dependencies[dependency_type] = DependencyDefinition(fn, params)
        return fn

    def register_for_type[T](
        self, dependency_type: Type[T]
    ) -> Callable[[SyncOrAsyncCallable[T]], SyncOrAsyncCallable[T]]:
        """Decorator to register a function as a provider for a specific type.

        Args:
            dependency_type: The type this provider satisfies.
        Returns:
            A decorator function.
        """

        def decorator(fn: SyncOrAsyncCallable[T]) -> SyncOrAsyncCallable[T]:
            params = self.get_parameters(fn)
            self._dependencies[dependency_type] = DependencyDefinition(fn, params)
            return fn

        return decorator

    def register_class[T](self, dependency_class: Type[T]) -> Type[T]:
        """Decorator to register a class as a dependency provider.

        Args:
            dependency_class: The class to register.
        Returns:
            The original class.
        """
        params = self.get_parameters(dependency_class)
        self._dependencies[dependency_class] = DependencyDefinition(dependency_class, params)
        return dependency_class

    def _get_object(self, dependency_type: Type[Any]) -> Any:
        if dependency_type in self._objects:
            return self._objects[dependency_type]

        if self.parent is not None:
            return self.parent._get_object(dependency_type)

        raise KeyError(dependency_type)

    def _get_definition(self, dependency_type: Type[Any]) -> DependencyDefinition:
        if dependency_type in self._dependencies:
            return self._dependencies[dependency_type]

        if self.parent is not None:
            return self.parent._get_definition(dependency_type)

        raise KeyError(dependency_type)

    @staticmethod
    def get_parameters(func: SyncOrAsyncCallable) -> dict[str, Type[Any]]:
        """Inspects a callable to extract its parameter names and types.

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
            if name in ["cls", "self"]:
                continue
            if param.annotation is inspect.Parameter.empty:
                raise TypeError(
                    f"Parameter '{name}' in {getattr(func, '__name__', str(func))} must have a type annotation"
                )
            if get_origin(param.annotation) is Annotated:
                param_type = get_args(param.annotation)[0]
            else:
                param_type = param.annotation
            params[name] = param_type
        return params

    def get(self, dependency_type: Type[Any], stack: set[Type] | None = None) -> Any:
        try:
            return self._get_object(dependency_type)
        except KeyError:
            pass

        stack = stack or set()

        if dependency_type in stack:
            raise RuntimeError(f"Cycle detected: {dependency_type}")

        stack.add(dependency_type)

        try:
            definition = self._get_definition(dependency_type)
        except KeyError:
            raise ValueError(f"Dependency of type {dependency_type} is not registered in DependencyContainer.")

        parameters = self.get_call_parameters(definition.params, stack)

        ret = definition.callable(**parameters)

        if inspect.isawaitable(ret):
            raise TypeError(f"Dependency '{dependency_type}' is asynchronous. Use 'get_async'.")

        # ważne: cache lokalny, nie parent
        self._objects[dependency_type] = ret

        return ret

    async def get_async(self, dependency_type: Type[Any], stack: set[Type] | None = None) -> Any:
        try:
            return self._get_object(dependency_type)
        except KeyError:
            pass

        stack = stack or set()

        if dependency_type in stack:
            raise RuntimeError(f"Cycle detected: {dependency_type}")

        stack.add(dependency_type)

        try:
            definition = self._get_definition(dependency_type)
        except KeyError:
            raise ValueError(f"Dependency of type {dependency_type} is not registered in DependencyContainer.")

        parameters = await self.get_call_parameters_async(definition.params, stack)
        ret = definition.callable(**parameters)

        if inspect.isawaitable(ret):
            ret = await ret

        # ważne: cache lokalny, nie parent
        self._objects[dependency_type] = ret
        return ret

    def get_call_parameters(self, params: dict[str, Type[Any]], stack: set[Type]) -> dict[str, Any]:
        """Resolves a dictionary of parameter types into their corresponding instances synchronously.

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
                parameters[param_name] = self.get(actual_type, stack)
            except ValueError:
                if is_optional:
                    parameters[param_name] = None
                    if actual_type in stack:
                        stack.discard(actual_type)
                else:
                    raise
        return parameters

    async def get_call_parameters_async(self, params: dict[str, Type[Any]], stack: set[Type]) -> dict[str, Any]:
        """Resolves a dictionary of parameter types into their corresponding instances asynchronously.

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
                parameters[param_name] = await self.get_async(actual_type, stack)
            except ValueError:
                if is_optional:
                    parameters[param_name] = None
                    if actual_type in stack:
                        stack.discard(actual_type)
                else:
                    raise
        return parameters
