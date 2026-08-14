import pytest

from ampf.dependency import DependencyRegistry


@pytest.fixture
def registry():
    yield DependencyRegistry()
    DependencyRegistry.clear()


class C[T]:
    def __init__(self, clazz: type[T]):
        self.value = clazz


class A:
    value: str = "A"


class B:
    value: str = "B"


def test_get_functional_dependency(registry: DependencyRegistry):
    # Given: Registered functional dependencies
    @DependencyRegistry.register
    def get_a() -> C[A]:
        return C(A)

    @DependencyRegistry.register
    def get_b() -> C[B]:
        return C(B)

    # When: Get dependency
    a = registry.get(C[A])
    b = registry.get(C[B])
    # Then: Dependencies are returned
    assert a.value.value == "A"
    assert b.value.value == "B"
    # And: The objects are stored
    assert registry.current()._objects[C[A]]
    assert registry.current()._objects[C[B]]
