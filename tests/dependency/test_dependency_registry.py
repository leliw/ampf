from dataclasses import dataclass, field
from typing import Any, Optional, Union

import pytest
from pydantic_settings import BaseSettings

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.base_factory import BaseFactory
from ampf.dependency import DependencyRegistry
from ampf.gcp.gcp_subscription_pull import GcpSubscriptionPull
from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from ampf.in_memory.in_memory_factory import InMemoryFactory


@pytest.fixture
def registry():
    yield DependencyRegistry()
    DependencyRegistry.clear()


class A:
    value: str = "A"

class C:
    pass

@dataclass
class B:
    a: A | C | None = None
    value: str = "B"


def test_get_functional_dependency(registry: DependencyRegistry):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)
    # When: Get dependency
    a = registry.get(A)
    # Then: Dependency is returned
    assert a.value == "A"


def test_get_functional_dependency_async_err(registry: DependencyRegistry):
    # Given: Registered async functional dependency
    async def get_a() -> A:
        return A()

    registry.register(get_a)
    # When: Get dependency
    with pytest.raises(TypeError):
        _ = registry.get(A)
    # Then: Error is raised


@pytest.mark.asyncio
async def test_get_async_functional_dependency_ok(registry: DependencyRegistry):
    # Given: Registered async functional dependency
    async def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)
    # When: Get dependency
    a = await registry.get_async(A)
    # Then: Dependency is returned
    assert a.value == "A"


def test_get_dependency_twice(registry: DependencyRegistry):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)
    # When: Get dependency
    a1 = registry.get(A)
    # And: Change value
    a1.value = "A1"
    # And: Get dependency again
    a2 = registry.get(A)
    # Then: The same object is returned
    assert a2.value == "A1"


@pytest.mark.asyncio
async def test_get_async_dependency_twice(registry: DependencyRegistry):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)
    # When: Get dependency
    a1 = await registry.get_async(A)
    # And: Change value
    a1.value = "A1"
    # And: Get dependency again
    a2 = await registry.get_async(A)
    # Then: The same object is returned
    assert a2.value == "A1"


def test_get_dependent_dependency(registry: DependencyRegistry):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)

    # And: Registered functional dependent dependency
    def get_b(a: A) -> B:
        return B(a)

    registry.register_for_type(B)(get_b)
    # When: Get dependency
    b = registry.get(B)
    # Then: Dependency is returned
    assert isinstance(b.a, A)
    assert b.a.value == "A"
    assert b.value == "B"


@pytest.mark.asyncio
async def test_get_async_dependent_dependency(registry: DependencyRegistry):
    # Given: Registered functional dependency
    async def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)

    # And: Registered functional dependent dependency
    async def get_b(a: A) -> B:
        return B(a)

    registry.register_for_type(B)(get_b)
    # When: Get dependency
    b = await registry.get_async(B)
    # Then: Dependency is returned
    assert isinstance(b.a, A)
    assert b.a.value == "A"
    assert b.value == "B"


def test_add_object(registry: DependencyRegistry):
    # Given: Added an object
    registry.add(A())
    # When: Get dependency
    a = registry.get(A)
    # Then: Dependency is returned
    assert a.value == "A"


def test_add_all(registry: DependencyRegistry):
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
    registry.add_all(app_state)
    # Then: The object is added
    assert registry.get(AppState) == app_state
    # And: All properties are added
    assert registry.get(AppConfig) == app_state.config
    assert registry.get(BaseFactory) == app_state.factory
    assert registry.get(BaseAsyncFactory) == app_state.async_factory


def test_circular_err(registry: DependencyRegistry):
    # Given: Two functions with circular dependency
    def get_a(b: B) -> A:
        return A()

    def get_b(a: A) -> B:
        return B(a)

    registry.register(get_a)
    registry.register(get_b)
    # When: Get dependency
    with pytest.raises(RuntimeError) as e:
        registry.get(A)
    # Then: An error is raised
    assert "Cycle detected" in str(e.value)


@pytest.mark.asyncio
async def test_circular_async_err(registry: DependencyRegistry):
    # Given: Two functions with circular dependency
    def get_a(b: B) -> A:
        return A()

    def get_b(a: A) -> B:
        return B(a)

    registry.register(get_a)
    registry.register(get_b)
    # When: Get dependency
    with pytest.raises(RuntimeError) as e:
        await registry.get_async(A)
    # Then: An error is raised
    assert "Cycle detected" in str(e.value)


def test_register_class(registry: DependencyRegistry):
    # Given: Registered class dependency
    @DependencyRegistry.register_class
    class C:
        def __init__(self, a: A):
            self.a = a

    def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)

    # When: Get dependency
    c = registry.get(C)

    # Then: Dependency is returned
    assert isinstance(c, C)
    assert c.a.value == "A"


def test_optional_dependency_missing(registry: DependencyRegistry):
    # Given: A function that depends on an Optional dependency that is not registered
    def get_b(a: Optional[A]) -> B:
        return B(a)

    registry.register_for_type(B)(get_b)

    # When: Get dependency
    b = registry.get(B)

    # Then: Dependency is returned with None for the optional parameter
    assert b.a is None
    assert b.value == "B"


@pytest.mark.asyncio
async def test_optional_dependency_missing_async(registry: DependencyRegistry):
    # Given: An async function that depends on an Optional dependency that is not registered
    async def get_b(a: Optional[A]) -> B:
        return B(a)

    registry.register_for_type(B)(get_b)

    # When: Get dependency
    b = await registry.get_async(B)

    # Then: Dependency is returned with None for the optional parameter
    assert b.a is None
    assert b.value == "B"


def test_complex_union_dependency_err(registry: DependencyRegistry):
    # Given: A function that depends on a complex Union dependency
    def get_b(a: Union[A, C, None]) -> B:
        return B(a)

    registry.register_for_type(B)(get_b)

    # When: Get dependency
    with pytest.raises(TypeError) as e:
        registry.get(B)

    # Then: An error is raised
    assert "Complex Union types are not supported" in str(e.value)


@pytest.mark.asyncio
async def test_complex_union_dependency_async_err(registry: DependencyRegistry):
    # Given: An async function that depends on a complex Union dependency
    async def get_b(a: Union[A, C, None]) -> B:
        return B(a)

    registry.register_for_type(B)(get_b)

    # When: Get dependency
    with pytest.raises(TypeError) as e:
        await registry.get_async(B)

    # Then: An error is raised
    assert "Complex Union types are not supported" in str(e.value)


def test_optional_dependency_no_cycle_false_positive(registry: DependencyRegistry):
    # Given: A tree where the same optional dependency is missing multiple times
    @dataclass
    class C:
        a: Optional[A]

    @dataclass
    class D:
        c: C
        a: Optional[A]

    registry.register_class(C)
    registry.register_class(D)

    # When: Get dependency
    d = registry.get(D)

    # Then: No cycle error is raised, and both optional dependencies are None
    assert d.a is None
    assert d.c.a is None


@pytest.mark.asyncio
async def test_optional_dependency_no_cycle_false_positive_async(
    registry: DependencyRegistry,
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

    registry.register_for_type(C)(get_c)
    registry.register_for_type(D)(get_d)

    # When: Get dependency
    d = await registry.get_async(D)

    # Then: No cycle error is raised, and both optional dependencies are None
    assert d.a is None
    assert d.c.a is None


def test_get_dependency_function(registry: DependencyRegistry):
    # Given: Registered functional dependency
    def get_a() -> A:
        return A()

    registry.register_for_type(A)(get_a)

    # When: Create dependency getter
    dep_getter = registry.get_dependency(A)

    # And: Call getter with registry
    a1 = dep_getter()

    # And: Call getter without registry (uses global DependencyRegistry)
    a2 = dep_getter()

    # Then: Dependencies are returned and are the same instance
    assert a1.value == "A" # pyright: ignore[reportAttributeAccessIssue]
    assert a2.value == "A" # pyright: ignore[reportAttributeAccessIssue]
    assert a1 is a2
