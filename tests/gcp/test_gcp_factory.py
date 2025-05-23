from pydantic import BaseModel
import pytest

from ampf.base.base_factory import CollectionDef
from ampf.gcp import GcpFactory


class T(BaseModel):
    name: str


def test_create_storage(gcp_factory: GcpFactory, collection_name: str):
    storage = gcp_factory.create_storage(collection_name, T, "name")
    assert storage is not None


def test_create_compact_storage(gcp_factory, collection_name: str):
    storage = gcp_factory.create_compact_storage(collection_name, T, "name")
    assert storage is not None


@pytest.fixture(scope="session")
def gcp_factory_with_root():
    return GcpFactory("root/path")


def test_create_storage_wr(gcp_factory_with_root: GcpFactory, collection_name: str):
    # Given: Storage with root
    storage_wr = gcp_factory_with_root.create_storage(collection_name, T, "name")
    # When: Item is stored with root
    storage_wr.save(T(name="XXX"))
    # Then: Item is stored in root
    coll_ref = storage_wr._db.collection("root/path/" + collection_name)
    ret = coll_ref.document("XXX").get().to_dict()
    assert ret["name"] == "XXX"
    # Clean up
    storage_wr.drop()


def test_create_collections_wr(gcp_factory_with_root: GcpFactory, collection_name: str):
    # Given: Colection definition
    c_def = CollectionDef(
        collection_name,
        T,
        key_name="name",
        subcollections=[CollectionDef("subcollection", T, key_name="name")],
    )
    # And: Storage with root
    collection_wr = gcp_factory_with_root.create_collection(c_def)
    # When: Item is stored in subbcollection with root
    collection_wr.save(T(name="XXX"))
    collection_wr.get_collection("XXX", "subcollection").save(T(name="YYY"))
    # Then: Item is stored in root
    coll_ref = collection_wr._db.collection(f"root/path/{collection_name}/XXX/subcollection")
    ret = coll_ref.document("YYY").get().to_dict()
    assert ret["name"] == "YYY"
    # Clean up
    collection_wr.drop()
