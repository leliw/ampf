import time
from typing import Dict, List, Optional

import pytest
import requests

try:
    import docker
    import docker.errors
    import docker.types
    from docker import DockerClient

    class ContainerNetworkFactory:
        def __init__(self, docker_client: Optional[DockerClient] = None):
            self.docker_client = docker_client or docker.from_env()
            self.created_networks = []

        def __call__(self, name: str):
            """Start a Docker network and return its ID.

            Args:
                name (str): Network name.
            Returns:
                str: ID of the started network.
            """
            try:
                network = self.docker_client.networks.get(name)
            except docker.errors.NotFound:
                network = self.docker_client.networks.create(name)
                self.created_networks.append(network)
            return network.id

        def cleanup(self):
            # Cleanup all started networks
            for network in self.created_networks:
                network.remove()

    class ContainerFactory:
        def __init__(self, docker_client: Optional[DockerClient] = None):
            self.docker_client = docker_client or docker.from_env()
            self.containers = []

        def __call__(
            self,
            image: str,
            name: str,
            ports: list[str] | None = None,
            command: Optional[str] = None,
            wait_for_http: str | None = None,
            timeout: int = 60,
            gpus: bool = False,
            environment: Optional[Dict[str, str]] = None,
            network: Optional[str] = None,
            volumes: Optional[Dict[str, Dict[str, str]] | List[str]] = None,
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
                environment (Optional[Dict[str, str]]): Environment varaibles
                network (Optional[str]): Network name
                valumes (Optional[Dict[str, Dict[str, str]] | List[str]]): Volumes to mount
            Returns:
                str: URL of the started container.
            """
            try:
                existing = self.docker_client.containers.get(name)
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass

            container = self.docker_client.containers.run(
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
                volumes=volumes,
            )
            self.containers.append(container)

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

        def cleanup(self):
            # Cleanup all started containers
            for c in self.containers:
                try:
                    c.stop()
                except Exception:
                    pass

    @pytest.fixture(scope="session")
    def docker_client():
        return docker.from_env()

    @pytest.fixture(scope="session")
    def container_network_factory(docker_client: docker.DockerClient) -> ContainerNetworkFactory:  # type: ignore
        """Fixture providing a factory to start Docker networks."""
        factory = ContainerNetworkFactory(docker_client)
        yield factory  # type: ignore
        factory.cleanup()

    @pytest.fixture(scope="session")
    def container_factory(docker_client: docker.DockerClient) -> ContainerFactory:  # type: ignore
        """Fixture providing a factory to start Docker containers."""
        factory = ContainerFactory(docker_client)
        yield factory  # type: ignore
        factory.cleanup()

except ImportError:
    pass