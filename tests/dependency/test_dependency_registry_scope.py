from dataclasses import dataclass

import pytest

from ampf.dependency.dependency_registry import DependencyRegistry


@pytest.fixture
def registry():
    yield DependencyRegistry()
    DependencyRegistry.clear()


@dataclass
class A:
    value: str = "A"

@dataclass
class B:
    value: A


def test_annotated_functional_dependency_in_scope(registry: DependencyRegistry):
    with registry.scope():
        # Given: Registered functional dependency by annotation inside scope
        @DependencyRegistry.register_for_type(A)
        def get_a() -> A:
            return A()
        # When: Get dependency inside scope
        a = registry.get(A)
        # Then: Dependency is returned
        assert a.value == "A"
    # When: Scope is closed
    # Then: The object is still stored
    assert A in registry.current()._objects

def test_object_in_scope(registry: DependencyRegistry):
    # Given: A scope
    with registry.scope() as scope:
        # And: An object added in the scope
        scope.add(A())
        # When: Get dependency inside scope
        a = registry.get(A)
        # Then: Dependency is returned
        assert a.value == "A"
        # And: The object is stored
        assert A in registry.current()._objects
    # When: Scope is closed
    # Then: The object is destroyed
    assert A not in registry.current()._objects

def test_definition_in_root_and_object_in_scope(registry: DependencyRegistry):
    # Given: Registered functional dependency by annotation outside scope
    @DependencyRegistry.register_for_type(B)
    def get_b(a: A) -> B:
        return B(value=a)
    # Given: A scope
    with registry.scope() as scope:
        # And: An object added in the scope
        scope.add(A())
        # When: Get dependency inside scope
        b = registry.get(B)
        # Then: Dependency is returned
        assert b.value.value == "A"
        # And: The objects are stored
        assert A in registry.current()._objects
        assert B in registry.current()._objects
    # When: Scope is closed
    # Then: The objects are destroyed
    assert A not in registry.current()._objects
    assert B not in registry.current()._objects

def test_object_in_root_and_definition_in_scope(registry: DependencyRegistry):
    # Given: Registered object outside scope
    registry.add(A())
    # And: A scope
    with registry.scope():
        # And: A definition inside scope
        @DependencyRegistry.register_for_type(B)
        def get_b(a: A) -> B:
            return B(value=a)
        # When: Get dependency inside scope
        b = registry.get(B)
        # Then: Dependency is returned
        assert b.value.value == "A"
        # And: The objects are not stored in scope
        assert A not in registry.current()._objects
        assert B not in registry.current()._objects
    # When: Scope is closed
    # Then: The objects are stored in root
    assert A in registry.current()._objects
    assert B in registry.current()._objects


def test_two_definitions_for_one_class(registry: DependencyRegistry):
    # Given: Registered functional dependency by annotation outside scope
    @DependencyRegistry.register_for_type(A)
    def get_a() -> A:
        return A(value="outside")

    with registry.scope():
        # And: Registered functional dependency by annotation inside scope
        @DependencyRegistry.register_for_type(A)
        def get_a() -> A:
            return A(value="inside")
        # When: Get dependency inside scope
        a = registry.get(A)
        # Then: Dependency is returned
        assert a.value == "inside"
    # When: Get dependency outside scope
    a = registry.get(A)
    # Then: Dependency defined outside is still available
    assert a.value == "outside"

def test_registered_twice(registry: DependencyRegistry):
    # Given: Registered functional dependency by annotation outside scope
    @DependencyRegistry.register_for_type(A)
    def get_a() -> A:
        return A(value="outside")

    with registry.scope():
        # And: Register the same inside scope
        DependencyRegistry.register_for_type(A)(get_a)
        # When: Get dependency inside scope
        a = registry.get(A)
        # Then: Dependency is returned
        assert a.value == "outside"
        # And: The object is not stored inside scope
        assert A not in registry.current()._objects
    # And: The object is stored outside scope
    assert registry.current()._objects[A]
    # When: Get dependency outside scope
    a = registry.get(A)
    # Then: Dependency defined outside is still available
    assert a.value == "outside"
