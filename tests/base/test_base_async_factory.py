from pathlib import Path
from uuid import UUID, uuid4
import pytest
from pydantic import BaseModel

from ampf.base import BaseAsyncFactory, BaseStorage
from ampf.base.base_factory import CollectionDef
from ampf.in_memory import InMemoryAsyncFactory
from ampf.local_async import AsyncLocalFactory




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
    name: str
    id: UUID


class D2(BaseModel):
    name: str
    id: UUID


class D3(BaseModel):
    name: str
    id: str

@pytest.mark.asyncio
async def test_create_storage_tree(tmp_path: Path):
    factory = AsyncLocalFactory(tmp_path)
    
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
    id1 = uuid4()
    await storage.save(D1(id=id1, name="foo"))

    # Then: Data is saved
    assert (tmp_path / "collections" / f"{id1}.json").exists()
    # And: The substorage is available (by name)
    substorage1 = storage.get_collection(id1, "documents")
    assert substorage1 is not None

    id2 = uuid4()
    await substorage1.save(D2(id=id2, name="bar"))
    assert (tmp_path / "collections" / f"{id1}" / "documents" / f"{id2}.json").exists()

    # And: The substorage is available (by class)
    substorage2 = storage.get_collection(id1, D2)
    assert substorage2 is not None
    # And: The substorage is available (by class)
    substorage3 = substorage2.get_collection(id2, D3)
    assert substorage3 is not None


if __name__ == "__main__":
    pytest.main([__file__])
