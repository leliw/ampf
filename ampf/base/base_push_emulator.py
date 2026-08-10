from __future__ import annotations

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import BaseModel

from ampf.shared.pubsub_message import PubsubMessage, PubsubRequest

# Importy wykonywane wyłącznie przez narzędzia do analizy typów (np. IDE, mypy)
if TYPE_CHECKING:
    from ampf.base.base_subscription import BaseSubscription

_log = logging.getLogger(__name__)


class BasePushEmulator[T: BaseModel]:
    """A base class for push emulators."""

    def __init__(self, subscription: BaseSubscription, clazz: type[T] | None = None):
        self.subscription = subscription
        self.clazz = clazz
        self.messages: list[PubsubMessage] = []
        self.payloads: list[T] = []
        self.responses: list[Response] = []
        self.client: TestClient | None = None
        self.endpoint_url: str = ""
        self.start_time = time.time()

    @contextmanager
    def run_push_emulator(self, client: TestClient, endpoint_url: str) -> Generator[Self]:
        self.client = client
        self.endpoint_url = endpoint_url
        self.start_time = time.time()
        yield self  # This method should be overridden in subclasses to provide actual push emulation behavior.

    def process_message(self, timeout: float):
        if not self.client:
            raise ValueError("PushEmulator isn't run")

        message = self.subscription.receive_message(timeout=timeout)
        if message:
            self.messages.append(message)
            if self.clazz:
                payload = message.decoded_data(self.clazz)
                self.payloads.append(payload)
            pubsub_req = PubsubRequest(message=message, subscription="ignored")
            response = self.client.post(self.endpoint_url, json=pubsub_req)
            if response:
                self.responses.append(response)

    def is_finished(
        self,
        timeout: float = 60.0,
        expected_responses: int = 1,
        per_message_timeout: float = 0.1,
    ) -> bool:
        """Checks if the emulator has finished processing messages.

        Args:
            timeout: The maximum time in seconds to wait for responses.
            expected_responses: The number of expected responses.
        Returns:
            True if the expected number of responses have been received or timeout occurred, False otherwise.
        """
        self.process_message(timeout=per_message_timeout)
        if time.time() >= self.start_time + timeout:
            _log.error("Timeout while waiting for responses")
            return True
        if len(self.responses) >= expected_responses:
            _log.info("All responses received")
            return True
        return False

    def wait_for(self, timeout: float = 60.0, expected_responses: int = 1) -> None:
        """Waits until the expected number of responses are received or timeout occurs.

        Args:
            timeout: The maximum time in seconds to wait for responses.
            expected_responses: The number of expected responses.
        """
        while not self.is_finished(timeout=timeout, expected_responses=expected_responses):
            time.sleep(0.2)

    def get_payloads(self) -> list[T]:
        """Returns the list of deserialized payloads.

        Returns:
            The list of deserialized payloads.
        """
        return self.payloads

    def get_responses(self) -> list[Response]:
        """Returns the list of sent responses.

        Returns:
            The list of responses.
        """
        return self.responses
