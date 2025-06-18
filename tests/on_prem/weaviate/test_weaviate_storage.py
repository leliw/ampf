import time
from typing import List, Optional, Tuple

import docker
import docker.errors
import pytest
import requests
from pydantic import BaseModel, Field

from ampf.base import KeyNotExistsException
from ampf.on_prem.weaviate import WeaviateDB, WeaviateStorage


@pytest.fixture(scope="session")
def weaviate_ports(docker_client: docker.DockerClient):
    container_name = "unittest_weaviate"
    container_image = "cr.weaviate.io/semitechnologies/weaviate:1.31.1"
    container_ports = ["8080/tcp", "50051/tcp"]
    try:
        existing = docker_client.containers.get(container_name)
        existing.remove(force=True)
    except docker.errors.NotFound:
        pass

    container = docker_client.containers.run(
        container_image,
        name=container_name,
        ports={container_ports[0]: None, container_ports[1]: None},  # Random ports
        detach=True,
        remove=True,
    )

    for _ in range(60):
        try:
            container.reload()
            if container.status == "running":
                port0 = container.ports[container_ports[0]][0]["HostPort"]
                port1 = container.ports[container_ports[1]][0]["HostPort"]
                requests.get(f"http://localhost:{port0}/docs")
                break
        except Exception:
            time.sleep(1)
    else:
        container.stop()
        pytest.fail("Container failed to start")

    yield (port0, port1)

    # Cleanup
    container.stop()


class D(BaseModel):
    name: str
    value: str
    prop1: Optional[str] = None
    prop2: Optional[str] = None
    prop3: Optional[str] = None
    embedding: List[float] = Field(default_factory=list)


@pytest.fixture
def storage(weaviate_ports: Tuple[int, int]):
    db = WeaviateDB(port=weaviate_ports[0], grpc_port=weaviate_ports[1])
    with db.connect() as db:
        yield WeaviateStorage("test", D, db=db, key_name="name", indexed_fields=["prop1", "prop2", "prop3"])


def test_storage_all(storage: WeaviateStorage):
    assert storage.is_empty()

    d = D(name="foo", value="beer")
    storage.put("foo", d)

    assert ["foo"] == list(storage.keys())
    assert d == storage.get("foo")

    assert not storage.is_empty()

    storage.delete("foo")
    assert [] == list(storage.keys())
    with pytest.raises(KeyNotExistsException):
        storage.get("foo")

    storage.put(d.name, d)
    storage.drop()
    assert [] == list(storage.keys())


def test_delete_where(storage: WeaviateStorage):
    assert storage.is_empty()

    storage.put("foo", D(name="foo1", value="beer1", prop1="foo"))
    storage.put("foo", D(name="foo2", value="beer2", prop1="foo"))
    storage.put("foo", D(name="beer", value="beer", prop1="beer"))

    ret = storage.get("foo1")
    assert ret.prop1 == "foo"

    storage.delete_where("prop1", "foo")

    keys = list(storage.keys())
    assert "foo1" not in keys
    assert "foo2" not in keys
    assert "beer" in keys

    storage.drop()
