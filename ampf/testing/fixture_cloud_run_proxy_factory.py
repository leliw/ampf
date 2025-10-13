import logging
import os
import signal
import socket
import subprocess
import time
from typing import Optional

import pytest

_log = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def cloud_run_proxy_factory():
    """Fixture providing a factory to start Cloud Run services."""
    processes = []

    def wait_for_port(port, host="127.0.0.1", timeout=30):
        """Wait for a port to become available."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection((host, int(port)), timeout=1):
                    return
            except OSError:
                time.sleep(0.5)
        raise TimeoutError(f"Port {port} on {host} did not become available within {timeout} seconds.")

    def get_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))  # Powiąż z portem 0, aby OS wybrał wolny port
            port = s.getsockname()[1]  # Pobierz przypisany numer portu
            return port

    def _start(service: str, region: str, port: Optional[int] = None):
        """Start a Cloud Run service and return its URL.

        Args:
            service (str): Cloud Run service name.
            region (str): Cloud Run region.
            port (int): Port to expose.

        Returns:
            str: URL of the started service.
        """
        port = port or get_free_port()
        proc = subprocess.Popen(
            ["gcloud", "run", "services", "proxy", service, "--region", region, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        processes.append(proc)
        wait_for_port(port)
        _log.info("Started proxy for %s in region %s on port %d", service, region, port)
        return f"http://127.0.0.1:{port}"

    yield _start

    for proc in processes:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()
