from dataclasses import dataclass, field
from typing import Any, Optional, Union

import pytest
from pydantic_settings import BaseSettings

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.base_factory import BaseFactory
from ampf.dependency.dependency_container import DependencyContainer
from ampf.gcp.gcp_subscription_pull import GcpSubscriptionPull
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from ampf.in_memory.in_memory_factory import InMemoryFactory


@pytest.fixture
def container():
    return DependencyContainer()


class A:
    value: str = "A"


class C:
    pass


@dataclass
class B:
    a: A | C | None = None
    value: str = "B"


def test_get_functional_dependency(container: DependencyContainer):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)
    # When: Get dependency
    a = container.get(A)
    # Then: Dependency is returned
    assert a.value == "A"


def test_get_functional_dependency_async_err(container: DependencyContainer):
    # Given: Registered async functional dependency
    async def get_a() -> A:
        return A()

    container.register(get_a)
    # When: Get dependency
    with pytest.raises(TypeError):
        _ = container.get(A)
    # Then: Error is raised


@pytest.mark.asyncio
async def test_get_async_functional_dependency_ok(container: DependencyContainer):
    # Given: Registered async functional dependency
    async def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)
    # When: Get dependency
    a = await container.get_async(A)
    # Then: Dependency is returned
    assert a.value == "A"


def test_get_dependency_twice(container: DependencyContainer):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)
    # When: Get dependency
    a1 = container.get(A)
    # And: Change value
    a1.value = "A1"
    # And: Get dependency again
    a2 = container.get(A)
    # Then: The same object is returned
    assert a2.value == "A1"


@pytest.mark.asyncio
async def test_get_async_dependency_twice(container: DependencyContainer):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)
    # When: Get dependency
    a1 = await container.get_async(A)
    # And: Change value
    a1.value = "A1"
    # And: Get dependency again
    a2 = await container.get_async(A)
    # Then: The same object is returned
    assert a2.value == "A1"


def test_get_dependent_dependency(container: DependencyContainer):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)

    # And: Registered functional dependent dependency
    def get_b(a: A) -> B:
        return B(a)

    container.register_for_type(B)(get_b)
    # When: Get dependency
    b = container.get(B)
    # Then: Dependency is returned
    assert isinstance(b.a, A)
    assert b.a.value == "A"
    assert b.value == "B"


@pytest.mark.asyncio
async def test_get_async_dependent_dependency(container: DependencyContainer):
    # Given: Registered functional dependency
    async def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)

    # And: Registered functional dependent dependency
    async def get_b(a: A) -> B:
        return B(a)

    container.register_for_type(B)(get_b)
    # When: Get dependency
    b = await container.get_async(B)
    # Then: Dependency is returned
    assert isinstance(b.a, A)
    assert b.a.value == "A"
    assert b.value == "B"


def test_add_object(container: DependencyContainer):
    # Given: Added an object
    container.add(A())
    # When: Get dependency
    a = container.get(A)
    # Then: Dependency is returned
    assert a.value == "A"


def test_add_all(container: DependencyContainer):
    # Given: A dataclass object
    class AppConfig(BaseSettings):
        data_dir: str = "./data"

    @dataclass
    class AppState:
        config: AppConfig
        factory: BaseFactory
        async_factory: BaseAsyncFactory
        subscriptions: dict[str, GcpSubscriptionPull] = field(default_factory=dict)
        ai_model: Any = None

    app_state = AppState(
        config=AppConfig(),
        factory=InMemoryFactory(),
        async_factory=InMemoryAsyncFactory(),
    )
    # When: All object properties are added
    container.add_all(app_state)
    # Then: The object is added
    assert container.get(AppState) == app_state
    # And: All properties are added
    assert container.get(AppConfig) == app_state.config
    assert container.get(BaseFactory) == app_state.factory
    assert container.get(BaseAsyncFactory) == app_state.async_factory


def test_circular_err(container: DependencyContainer):
    # Given: Two functions with circular dependency
    def get_a(b: B) -> A:
        return A()

    def get_b(a: A) -> B:
        return B(a)

    container.register(get_a)
    container.register(get_b)
    # When: Get dependency
    with pytest.raises(RuntimeError) as e:
        container.get(A)
    # Then: An error is raised
    assert "Cycle detected" in str(e.value)


@pytest.mark.asyncio
async def test_circular_async_err(container: DependencyContainer):
    # Given: Two functions with circular dependency
    def get_a(b: B) -> A:
        return A()

    def get_b(a: A) -> B:
        return B(a)

    container.register(get_a)
    container.register(get_b)
    # When: Get dependency
    with pytest.raises(RuntimeError) as e:
        await container.get_async(A)
    # Then: An error is raised
    assert "Cycle detected" in str(e.value)


def test_register_class(container: DependencyContainer):
    # Given: Registered class dependency
    @container.register_class
    class C:
        def __init__(self, a: A):
            self.a = a

    def get_a() -> A:
        return A()

    container.register_for_type(A)(get_a)

    # When: Get dependency
    c = container.get(C)

    # Then: Dependency is returned
    assert isinstance(c, C)
    assert c.a.value == "A"


def test_optional_dependency_missing(container: DependencyContainer):
    # Given: A function that depends on an Optional dependency that is not registered
    def get_b(a: Optional[A]) -> B:
        return B(a)

    container.register_for_type(B)(get_b)

    # When: Get dependency
    b = container.get(B)

    # Then: Dependency is returned with None for the optional parameter
    assert b.a is None
    assert b.value == "B"


@pytest.mark.asyncio
async def test_optional_dependency_missing_async(container: DependencyContainer):
    # Given: An async function that depends on an Optional dependency that is not registered
    async def get_b(a: Optional[A]) -> B:
        return B(a)

    container.register_for_type(B)(get_b)

    # When: Get dependency
    b = await container.get_async(B)

    # Then: Dependency is returned with None for the optional parameter
    assert b.a is None
    assert b.value == "B"


def test_complex_union_dependency_err(container: DependencyContainer):
    # Given: A function that depends on a complex Union dependency
    def get_b(a: Union[A, C, None]) -> B:
        return B(a)

    container.register_for_type(B)(get_b)

    # When: Get dependency
    with pytest.raises(TypeError) as e:
        container.get(B)

    # Then: An error is raised
    assert "Complex Union types are not supported" in str(e.value)


@pytest.mark.asyncio
async def test_complex_union_dependency_async_err(container: DependencyContainer):
    # Given: An async function that depends on a complex Union dependency
    async def get_b(a: Union[A, C, None]) -> B:
        return B(a)

    container.register_for_type(B)(get_b)

    # When: Get dependency
    with pytest.raises(TypeError) as e:
        await container.get_async(B)

    # Then: An error is raised
    assert "Complex Union types are not supported" in str(e.value)


def test_optional_dependency_no_cycle_false_positive(container: DependencyContainer):
    # Given: A tree where the same optional dependency is missing multiple times
    @dataclass
    class C:
        a: Optional[A]

    @dataclass
    class D:
        c: C
        a: Optional[A]

    container.register_class(C)
    container.register_class(D)

    # When: Get dependency
    d = container.get(D)

    # Then: No cycle error is raised, and both optional dependencies are None
    assert d.a is None
    assert d.c.a is None


@pytest.mark.asyncio
async def test_optional_dependency_no_cycle_false_positive_async(
    container: DependencyContainer,
):
    # Given: A tree where the same optional dependency is missing multiple times
    @dataclass
    class C:
        a: Optional[A]

    @dataclass
    class D:
        c: C
        a: Optional[A]

    async def get_c(a: Optional[A]) -> C:
        return C(a)

    async def get_d(c: C, a: Optional[A]) -> D:
        return D(c, a)

    container.register_for_type(C)(get_c)
    container.register_for_type(D)(get_d)

    # When: Get dependency
    d = await container.get_async(D)

    # Then: No cycle error is raised, and both optional dependencies are None
    assert d.a is None
    assert d.c.a is None
