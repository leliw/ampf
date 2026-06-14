import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Type

from ampf.dependency.dependency_container import DependencyContainer

from .dependency_model import SyncOrAsyncCallable

_log = logging.getLogger(__name__)
_root_container = DependencyContainer()
_current_container: ContextVar[DependencyContainer] = ContextVar(
    "current_dependency_container",
    default=_root_container,
)


class DependencyRegistry:
    """
    A registry for managing and resolving synchronous and asynchronous dependencies.
    """

    @classmethod
    def current(cls) -> DependencyContainer:
        return _current_container.get()

    @classmethod
    @contextmanager
    def scope(cls):
        parent = cls.current()
        scoped = parent.create_scope()
        token = _current_container.set(scoped)

        try:
            yield scoped
        finally:
            _current_container.reset(token)

    @classmethod
    def clear(cls) -> None:
        """
        Clears all registered dependencies and cached object instances.
        """
        cls.current().clear()

    @classmethod
    def clear_objects(cls) -> None:
        """
        Clears all cached object instances.
        """
        cls.current().clear_objects()
        _log.debug("All objects cleared in registry")

    @classmethod
    def add(cls, instance: Any, instance_type: Type[Any] | None = None) -> None:
        """
        Manually adds an object instance to the registry.

        Args:
            instance: The instance to add.
            instance_type: Optional type to register the object under. Defaults to object.__class__.
        """
        cls.current().add(instance, instance_type)
        _log.debug("Added object to registry: %s", instance_type or instance.__class__)

    @classmethod
    def add_all(cls, instance: Any) -> None:
        """
        Adds an object and its dataclass fields to the registry if they are not built-in types.

        Args:
            instance: The object whose fields should be registered.
        """
        cls.current().add_all(instance)

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
        return cls.current().register(fn)

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
        return cls.current().register_for_type(dependency_type)

    @classmethod
    def register_class[T](cls, dependency_class: Type[T]) -> Type[T]:
        """
        Decorator to register a class as a dependency provider.

        Args:
            dependency_class: The class to register.

        Returns:
            The original class.
        """
        return cls.current().register_class(dependency_class)

    @classmethod
    def get[T](cls, dependency_type: Type[T]) -> T:
        """
        Synchronously retrieves or creates an instance of a registered dependency.

        Args:
            dependency_type: The type of the dependency to retrieve.

        Returns:
            An instance of the requested dependency.

        Raises:
            RuntimeError: If a circular dependency is detected.
            ValueError: If the dependency type is not registered.
            TypeError: If the dependency provider is asynchronous.
        """
        return cls.current().get(dependency_type)

    @classmethod
    async def get_async[T](cls, dependency_type: Type[T]) -> T:
        """
        Asynchronously retrieves or creates an instance of a registered dependency.

        Args:
            dependency_type: The type of the dependency to retrieve.

        Returns:
            An instance of the requested dependency.

        Raises:
            RuntimeError: If a circular dependency is detected.
            ValueError: If the dependency type is not registered.
        """
        return await cls.current().get_async(dependency_type)


def get_dependency[T](clazz: Type[T]) -> SyncOrAsyncCallable[T]:
    """Returns a function that retrieves a dependency of the specified type from the DependencyRegistry.

    Args:
        clazz (Type[T]): The type of the dependency to retrieve.

    Returns:
        A callable that returns an instance of the requested dependency when called.
    """

    def ret_dep() -> T:
        return DependencyRegistry.get(clazz)

    return ret_dep
