from pydantic import BaseModel
import pytest

from ampf.base import BaseFactory, BaseStorage
from ampf.in_memory import InMemoryFactory


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def factory():
    return InMemoryFactory()


def test_crete_compact_storage(factory: BaseFactory):
    # When: A compact storage is created
    s1 = factory.create_compact_storage("xxx", D)
    # Then: A storage is created
    assert s1 is not None
    assert issubclass(s1.__class__, BaseStorage)


def test_crete_storage_with_key(factory: BaseFactory):
    # When: A compact storage is created
    s1 = factory.create_storage("xxx", D, key=lambda d: d.name)
    # Then: A storage is created
    assert s1 is not None
    assert issubclass(s1.__class__, BaseStorage)

if __name__ == "__main__":
    pytest.main([__file__])
