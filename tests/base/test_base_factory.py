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

