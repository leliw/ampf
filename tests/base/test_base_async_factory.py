import pytest
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseStorage
from ampf.base.base_async_collection_storage import BaseAsyncCollectionStorage
from ampf.base.base_factory import CollectionDef
from ampf.in_memory import InMemoryAsyncFactory


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def factory():
    return InMemoryAsyncFactory()


def test_crete_compact_storage(factory: BaseAsyncFactory):
    # When: A compact storage is created
    s1 = factory.create_compact_storage("xxx", D)
    # Then: A storage is created
    assert s1 is not None
    assert issubclass(s1.__class__, BaseStorage)


def test_crete_storage_with_key(factory: BaseAsyncFactory):
    # When: A compact storage is created
    s1 = factory.create_storage("xxx", D, key=lambda d: d.name)
    # Then: A storage is created
    assert s1 is not None
    assert issubclass(s1.__class__, BaseStorage)


class D1(BaseModel):
    id: str
    name: str


class D2(BaseModel):
    id: str
    name: str


class D3(BaseModel):
    id: str
    name: str


def test_create_storage_tree(factory: BaseAsyncFactory):
    # Given: A storage tree definition
    storage_def = CollectionDef(
        "collections",
        D1,
        "id",
        [
            CollectionDef(
                "documents",
                D2,
                "id",
                [
                    CollectionDef("markdowns", D3, "id"),
                ],
            )
        ],
    )
    # When: The storage tree is created
    storage = factory.create_collection(storage_def)
    # Then: The storage tree is created
    assert storage is not None
    assert issubclass(storage.__class__, BaseAsyncCollectionStorage)
    # And: The substorage is available (by name)
    substorage = storage.get_collection("1", "documents")
    assert substorage is not None
    # And: The substorage is available (by class)
    substorage = storage.get_collection("1", D2)
    assert substorage is not None


if __name__ == "__main__":
    pytest.main([__file__])
