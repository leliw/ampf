from pydantic import BaseModel

from ampf.gcp import GcpFactory


class T(BaseModel):
    name: str


def test_create_storage(gcp_factory: GcpFactory, collection_name: str):
    storage = gcp_factory.create_storage(collection_name, T, "name")
    assert storage is not None


def test_create_compact_storage(gcp_factory, collection_name: str):
    storage = gcp_factory.create_compact_storage(collection_name, T, "name")
    assert storage is not None
