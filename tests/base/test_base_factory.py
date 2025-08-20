from pathlib import Path

import pytest
from pydantic import BaseModel

from ampf.base import BaseFactory, BaseStorage
from ampf.base.base_factory import CollectionDef
from ampf.in_memory import InMemoryFactory
from ampf.local.local_factory import LocalFactory


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


class D1(BaseModel):
    id: str
    name: str


class D2(BaseModel):
    id: str
    name: str


class D3(BaseModel):
    id: str
    name: str


def test_create_storage_tree(tmp_path: Path):
    factory = LocalFactory(tmp_path)
    
    # Given: A storage tree definition
    storage_def = CollectionDef("collections", D1, "id", [
            CollectionDef("documents", D2, "id", [
                    CollectionDef("markdowns", D3, "id"),
                ],
            )
        ],
    )
    
    # When: The storage tree is created
    storage = factory.create_storage_tree(storage_def)
    # And: Storage saves data
    storage.save(D1(id="1", name="foo"))

    # Then: Data is saved
    assert (tmp_path / "collections" / "1.json").exists()
    # And: The substorage is available (by name)
    substorage1 = storage.get_collection("1", "documents")
    assert substorage1 is not None

    substorage1.save(D2(id="2", name="bar"))
    assert (tmp_path / "collections" / "1" / "documents" / "2.json").exists()

    # And: The substorage is available (by class)
    substorage2 = storage.get_collection("1", D2)
    assert substorage2 is not None
    # And: The substorage is available (by class)
    substorage3 = substorage2.get_collection("1", D3)
    assert substorage3 is not None


if __name__ == "__main__":
    pytest.main([__file__])
