import inspect
import logging
import types
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

from ampf.dependency.dependency_model import DependencyDefinition, SyncOrAsyncCallable

_log = logging.getLogger(__name__)


class DependencyContainer:
    def __init__(self, parent: "DependencyContainer | None" = None) -> None:
        self.parent = parent
        self.level = parent.level + 1 if parent else 0
        self._dependencies: dict[type[Any], DependencyDefinition] = {}
        self._objects: dict[type[Any], Any] = {}

    def root(self) -> "DependencyContainer":
        ret = self
        while ret.parent:
            ret = ret.parent
        return ret

    def create_scope(self) -> "DependencyContainer":
        return DependencyContainer(parent=self)

    def clear(self) -> None:
        """Clears all registered dependencies and cached object instances."""
        self._dependencies = {}
        self._objects = {}

    def clear_objects(self) -> None:
        """Clears all cached object instances."""
        self._objects = {}

    def add(self, instance: Any, instance_type: type[Any] | None = None) -> None:
        self._objects[instance_type or instance.__class__] = instance
        _log.debug("Add object at level %d of class %s", self.level, instance_type or instance.__class__)

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
                if value is not None and not isinstance(value, type):
                    actual_type, _ = self.get_actual_type_optional(declared_type)
                    if isinstance(actual_type, type) and getattr(actual_type, "__module__", None) != "builtins":
                        self.add(value, actual_type)

    @staticmethod
    def get_actual_type_optional(defined_type: Any) -> tuple[type[Any], bool]:
        origin = get_origin(defined_type)
        args = get_args(defined_type)
        is_optional = False
        actual_type = defined_type

        if (origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)) and type(None) in args:
            is_optional = True
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) > 1:
                raise TypeError(f"Complex Union types are not supported for dependency injection: {defined_type}")
            actual_type = non_none_args[0]
        return actual_type, is_optional

    def register[**P, R](self, fn: Callable[P, R]) -> Callable[P, R]:
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
        self._add_definition(dependency_type, DependencyDefinition(fn, params))
        return fn

    def register_for_type[T, **P, R](self, dependency_type: type[T]) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Decorator to register a function as a provider for a specific type.

        Args:
            dependency_type: The type this provider satisfies.
        Returns:
            A decorator function.
        """

        def decorator(fn: Callable[P, R]) -> Callable[P, R]:
            params = self.get_parameters(fn)
            self._add_definition(dependency_type, DependencyDefinition(fn, params))
            return fn

        return decorator

    def register_class[T](self, dependency_class: type[T], dependency_type: type[Any] | None = None) -> type[T]:
        """Decorator to register a class as a dependency provider.

        Args:
            dependency_class: The class to register.
            dependency_type: The type this class satisfies.

        Returns:
            The original class.
        """
        if dependency_type and not issubclass(dependency_class, dependency_type):
            raise RuntimeError(f"{dependency_class} must be a subclass of {dependency_type}.")
        params = self.get_parameters(dependency_class)
        self._add_definition(dependency_type or dependency_class, DependencyDefinition(dependency_class, params))
        return dependency_class

    def _get_object(self, dependency_type: type[Any]) -> tuple[Any, "DependencyContainer"]:
        if dependency_type in self._objects:
            return (self._objects[dependency_type], self)

        if self.parent is not None:
            return self.parent._get_object(dependency_type)

        raise KeyError(dependency_type)

    def _add_definition(self, dependency_type: type[Any], dependency_definition: DependencyDefinition) -> None:
        # Search for first parent without this definition
        current = self
        while current.parent and dependency_type not in current.parent._dependencies:
            current = current.parent
        if current.parent and current.parent._dependencies[dependency_type] == dependency_definition:
            # This definition is already stored
            return
        # Add definition to this parent
        current._dependencies[dependency_type] = dependency_definition
        _log.debug("Add definition at level %d of class %s", current.level, dependency_type)

    def _get_definition(self, dependency_type: type[Any]) -> tuple[DependencyDefinition, "DependencyContainer"]:

        if dependency_type in self._dependencies:
            return (self._dependencies[dependency_type], self)

        if self.parent is not None:
            return self.parent._get_definition(dependency_type)

        raise KeyError(dependency_type)

    @staticmethod
    def get_parameters(func: SyncOrAsyncCallable) -> dict[str, type[Any]]:
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

    def get[T](self, dependency_type: type[T]) -> T:
        return self._get(dependency_type)[0]

    def _get(self, dependency_type: type[Any], stack: set[type] | None = None) -> tuple[Any, "DependencyContainer"]:
        try:
            return self._get_object(dependency_type)
        except KeyError:
            pass

        stack = stack or set()

        if dependency_type in stack:
            raise RuntimeError(f"Cycle detected: {dependency_type}")

        stack.add(dependency_type)

        try:
            definition, def_container = self._get_definition(dependency_type)
        except KeyError:
            _log.info("Dependency of type %s is not registered in DependencyContainer.", dependency_type)
            _log.debug("Registered definitions: %s", [d for d in self._dependencies])
            raise ValueError(f"Dependency of type {dependency_type} is not registered in DependencyContainer.")

        parameters, param_container = self.get_call_parameters(definition.params, stack)

        ret = definition.callable(**parameters)

        if inspect.isawaitable(ret):
            raise TypeError(f"Dependency '{dependency_type}' is asynchronous. Use 'get_async'.")

        container = def_container if def_container.level > param_container.level else param_container
        container._objects[dependency_type] = ret

        return (ret, container)

    async def get_async(self, dependency_type: type[Any]) -> Any:
        return (await self._get_async(dependency_type))[0]

    async def _get_async(
        self, dependency_type: type[Any], stack: set[type] | None = None
    ) -> tuple[Any, "DependencyContainer"]:
        try:
            return self._get_object(dependency_type)
        except KeyError:
            pass

        stack = stack or set()

        if dependency_type in stack:
            raise RuntimeError(f"Cycle detected: {dependency_type}")

        stack.add(dependency_type)

        try:
            definition, def_container = self._get_definition(dependency_type)
        except KeyError:
            _log.info("Dependency of type %s is not registered in DependencyContainer.", dependency_type)
            _log.debug("Registered definitions: %s", [d for d in self._dependencies])
            raise ValueError(f"Dependency of type {dependency_type} is not registered in DependencyContainer.")

        parameters, param_container = await self.get_call_parameters_async(definition.params, stack)
        ret = definition.callable(**parameters)

        if inspect.isawaitable(ret):
            ret = await ret

        container = def_container if def_container.level > param_container.level else param_container
        container._objects[dependency_type] = ret
        return (ret, container)

    def get_call_parameters(
        self, params: dict[str, type[Any]], stack: set[type]
    ) -> tuple[dict[str, Any], "DependencyContainer"]:
        """Resolves a dictionary of parameter types into their corresponding instances synchronously.

        Args:
            params: Dictionary of parameter names and types.
            stack: Current resolution stack for cycle detection.
        Returns:
            A dictionary of parameter names and resolved instances.
        """
        parameters = {}
        container = self.root()
        for param_name, param_type in params.items():
            actual_type, is_optional = self.get_actual_type_optional(param_type)
            try:
                parameters[param_name], con = self._get(actual_type, stack)
                if con.level > container.level:
                    container = con
            except ValueError:
                if is_optional:
                    parameters[param_name] = None
                    if actual_type in stack:
                        stack.discard(actual_type)
                else:
                    raise
        return (parameters, container)

    async def get_call_parameters_async(
        self, params: dict[str, type[Any]], stack: set[type]
    ) -> tuple[dict[str, Any], "DependencyContainer"]:
        """Resolves a dictionary of parameter types into their corresponding instances asynchronously.

        Args:
            params: Dictionary of parameter names and types.
            stack: Current resolution stack for cycle detection.
        Returns:
            A dictionary of parameter names and resolved instances.
        """
        parameters = {}
        container = self.root()
        for param_name, param_type in params.items():
            actual_type, is_optional = self.get_actual_type_optional(param_type)
            try:
                parameters[param_name], con = await self._get_async(actual_type, stack)
                if con.level > container.level:
                    container = con
            except ValueError:
                if is_optional:
                    parameters[param_name] = None
                    if actual_type in stack:
                        stack.discard(actual_type)
                else:
                    raise
        return (parameters, container)
