import time
from typing import List, Tuple

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
    embedding: List[float] = Field(default_factory=list)


@pytest.fixture
def storage(weaviate_ports: Tuple[int, int]):
    db = WeaviateDB(port=weaviate_ports[0], grpc_port=weaviate_ports[1])
    with db.connect() as db:
        yield WeaviateStorage("test", D, db=db)


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
