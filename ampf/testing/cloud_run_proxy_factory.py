import logging
import os
import signal
import socket
import subprocess
import time

import pytest

_log = logging.getLogger(__name__)


class CloudRunProxyFactory:
    def __init__(self) -> None:
        self.processes = []

    def wait_for_port(self, port: int, host: str = "127.0.0.1", timeout: int = 60):
        """Wait for a port to become available."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection((host, int(port)), timeout=1):
                    return
            except OSError:
                time.sleep(0.5)
        raise TimeoutError(f"Port {port} on {host} did not become available within {timeout} seconds.")

    def get_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))  #
            port = s.getsockname()[1]  # Pobierz przypisany numer portu
            return port

    def __call__(
        self, service: str, region: str, project: str | None = None, port: int | None = None, timeout: int = 60
    ):
        """Start a Cloud Run service and return its URL.

        Args:
            service (str): Cloud Run service name.
            region (str): Cloud Run region.
            project (str | None): Cloud Run project.
            port (int | None): Port to expose.
            timeout (int): How long to wait for service readiness.
        Returns:
            str: URL of the started service.
        """
        port = port or self.get_free_port()
        assert port
        args = ["gcloud", "run", "services", "proxy", service, "--region", region, "--port", str(port)]
        if project:
            args.extend(["--project", project])
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        self.processes.append(proc)
        try:
            self.wait_for_port(port, timeout=timeout)
        except TimeoutError as e:
            proc.terminate()
            try:
                _, stderr = proc.communicate(timeout=5)
                err = stderr.decode("utf-8") if stderr else ""
            except subprocess.TimeoutExpired:
                proc.kill()
                _, stderr = proc.communicate()
                err = stderr.decode("utf-8") if stderr else ""
            if err:
                raise RuntimeError(f"Failed to start proxy for {service} in region {region}: {err}")
            raise e
        _log.info("Started proxy for %s in region %s on port %d", service, region, port)
        return f"http://127.0.0.1:{port}"

    def cleanup(self) -> None:
        for proc in self.processes:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait()
            except OSError:
                pass


@pytest.fixture(scope="session")
def cloud_run_proxy_factory() -> CloudRunProxyFactory:  # type: ignore
    """Fixture providing a factory to start Cloud Run services."""

    factory = CloudRunProxyFactory()
    yield factory  # type: ignore
    factory.cleanup()
