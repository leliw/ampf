import time
from typing import Optional

import pytest
import requests

try:
    import docker
    import docker.errors
    import docker.types

    @pytest.fixture(scope="session")
    def docker_client():
        return docker.from_env()

    @pytest.fixture(scope="session")
    def container_network_factory(docker_client: docker.DockerClient):
        """Fixture providing a factory to start Docker networks."""

        created_networks = []

        def _start_network(name: str):
            """Start a Docker network and return its ID.

            Args:
                name (str): Network name.
            Returns:
                str: ID of the started network.
            """
            try:
                network = docker_client.networks.get(name)
            except docker.errors.NotFound:
                network = docker_client.networks.create(name)
                created_networks.append(network)
            return network.id

        yield _start_network

        # Cleanup all started networks
        for network in created_networks:
            network.remove()

    @pytest.fixture(scope="session")
    def container_factory(docker_client: docker.DockerClient):  # type: ignore
        """Fixture providing a factory to start Docker containers."""

        containers = []

        def _start_container(
            image: str,
            name: str,
            ports: list[str] | None = None,
            command: Optional[str] = None,
            wait_for_http: str | None = None,
            timeout: int = 60,
            gpus: bool = False,
            environment: Optional[dict[str, str]] = None,
            network: Optional[str] = None,
        ) -> str:
            """Start a Docker container and return exposed host port.

            Args:
                image (str): Docker image.
                name (str): Container name.
                ports (list[str]): Container ports to expose.
                command (Optional[str]): Command to run in the container.
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
                command=command,
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
                environment=environment,
                network=network,
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
except ImportError:

    @pytest.fixture(scope="session")
    def container_factory(docker_client):
        raise RuntimeError("Docker SDK is not installed")

    @pytest.fixture(scope="session")
    def container_network_factory(docker_client):
        raise RuntimeError("Docker SDK is not installed")
