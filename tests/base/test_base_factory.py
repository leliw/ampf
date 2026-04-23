from pathlib import Path
from uuid import UUID, uuid4

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


def test_create_compact_storage(factory: BaseFactory):
    # When: A compact storage is created
    s1 = factory.create_compact_storage("xxx", D)
    # Then: A storage is created
    assert s1 is not None
    assert issubclass(s1.__class__, BaseStorage)


def test_create_storage_with_key(factory: BaseFactory):
    # When: A compact storage is created
    s1 = factory.create_storage("xxx", D, key=lambda d: d.name)
    # Then: A storage is created
    assert s1 is not None
    assert issubclass(s1.__class__, BaseStorage)


class D1(BaseModel):
    name: str
    id: UUID


class D2(BaseModel):
    name: str
    id: UUID


class D3(BaseModel):
    name: str
    id: UUID


def test_create_storage_tree(tmp_path: Path):
    factory = LocalFactory(tmp_path)

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
    storage = factory.create_storage_tree(storage_def)
    # And: Storage saves data
    id1 = uuid4()
    storage.save(D1(id=id1, name="foo"))

    # Then: Data is saved
    assert (tmp_path / "collections" / f"{id1}.json").exists()
    # And: The substorage is available (by name)
    substorage1 = storage.get_collection(id1, "documents")
    assert substorage1 is not None

    id2 = uuid4()
    substorage1.save(D2(id=id2, name="bar"))
    assert (tmp_path / "collections" / f"{id1}" / "documents" / f"{id2}.json").exists()

    # And: The substorage is available (by class)
    substorage2 = storage.get_collection(id1, D2)
    assert substorage2 is not None
    # And: The substorage is available (by class)
    substorage3 = substorage2.get_collection(id2, D3)
    assert substorage3 is not None


if __name__ == "__main__":
    pytest.main([__file__])


def test_register_and_get_collection(factory: BaseFactory):
    from ampf.base.exceptions import KeyNotExistsException

    # Given: A collection definition
    storage_def = CollectionDef("my_collection", D, "name")

    # When: The collection is registered
    factory.register_collections([storage_def])

    # Then: The collection can be retrieved by name
    storage = factory.get_collection("my_collection")
    assert storage is not None
    assert storage.decorated.collection_name == "my_collection"

    # And: The collection can be retrieved by type
    storage_by_type = factory.get_collection(D)
    assert storage_by_type is not None
    assert storage_by_type.decorated.collection_name == "my_collection"

    # And: Saving data works
    storage.save(D(name="test", value="val"))
    assert storage.get("test").value == "val"

    # And: Getting an unregistered collection raises an exception
    with pytest.raises(KeyNotExistsException):
        factory.get_collection("non_existent")

    # And: Getting an unregistered type raises an exception
    class UnregisteredModel(BaseModel):
        pass

    with pytest.raises(KeyNotExistsException):
        factory.get_collection(UnregisteredModel)
