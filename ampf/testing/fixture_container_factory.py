import time

import docker
import docker.errors
import docker.types
import pytest
import requests


@pytest.fixture(scope="session")
def docker_client():
    return docker.from_env()


@pytest.fixture(scope="session")
def container_factory(docker_client: docker.DockerClient):
    """Fixture providing a factory to start Docker containers."""

    containers = []

    def _start_container(
        image: str,
        name: str,
        ports: list[str] | None = None,
        wait_for_http: str | None = None,
        timeout: int = 60,
        gpus: bool = False,
    ) -> str:
        """Start a Docker container and return exposed host port.

        Args:
            image (str): Docker image.
            name (str): Container name.
            ports (list[str]): Container ports to expose.
            wait_for_http (str): Optional path to check service readiness, e.g. '/docs'.
            timeout (int): How long to wait for container readiness.
            gpus (bool): Whether to use GPUs.
        Returns:
            str: URL of the started container.
        """
        try:
            existing = docker_client.containers.get(name)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        container = docker_client.containers.run(
            image,
            name=name,
            ports={port: None for port in (ports or [])},
            detach=True,
            remove=True,
            device_requests=[
                docker.types.DeviceRequest(
                    count=-1,
                    capabilities=[["gpu"]],
                )
            ]
            if gpus
            else None,
        )
        containers.append(container)

        # wait for container
        start = time.time()
        while time.time() - start < timeout:
            try:
                container.reload()
                if container.status == "running" and container.ports:
                    mapped_ports = [container.ports[p][0]["HostPort"] for p in container.ports]
                    url = f"http://localhost:{mapped_ports[0]}"
                    if wait_for_http:
                        requests.get(f"{url}{wait_for_http}")
                    return url
            except Exception:
                pass
            time.sleep(1)

        container.stop()
        pytest.fail(f"Container {name} failed to start")

    yield _start_container

    # Cleanup all started containers
    for c in containers:
        try:
            c.stop()
        except Exception:
            pass
