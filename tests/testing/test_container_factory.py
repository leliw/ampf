import pytest
import requests

from ampf.testing import ContainerFactory

@pytest.fixture(scope="session")
def chunker_url(container_factory: ContainerFactory) ->str:
    """Fixture using the factory to start Chunker service."""
    return container_factory(
        image="europe-west3-docker.pkg.dev/development-428212/docker-eu/pdf2markdown:latest",
        name="unittest_chunker_service",
        ports=["8080/tcp"],
        wait_for_http="/docs",
        gpus=False,
    )


def test_container_factory(chunker_url: str):
    try:
        requests.get(f"{chunker_url}/openapi.json", timeout=1)
    except requests.ReadTimeout:
        assert False
    assert True
