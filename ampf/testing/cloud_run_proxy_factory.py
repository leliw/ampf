import logging
import os
import signal
import socket
import subprocess
import time
from typing import Optional

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

    def __call__(self, service: str, region: str, port: Optional[int] = None, timeout: int = 60):
        """Start a Cloud Run service and return its URL.

        Args:
            service (str): Cloud Run service name.
            region (str): Cloud Run region.
            port (int): Port to expose.
            timeout (int): How long to wait for service readiness.
        Returns:
            str: URL of the started service.
        """
        port = port or self.get_free_port()
        assert port
        proc = subprocess.Popen(
            ["gcloud", "run", "services", "proxy", service, "--region", region, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        self.processes.append(proc)
        self.wait_for_port(port, timeout=timeout)
        _log.info("Started proxy for %s in region %s on port %d", service, region, port)
        return f"http://127.0.0.1:{port}"

    def cleanup(self) -> None:
        for proc in self.processes:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait()


@pytest.fixture(scope="session")
def cloud_run_proxy_factory() -> CloudRunProxyFactory: # type: ignore
    """Fixture providing a factory to start Cloud Run services."""
    
    factory = CloudRunProxyFactory()
    yield factory # type: ignore
    factory.cleanup()

