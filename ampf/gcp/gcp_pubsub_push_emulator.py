import logging
import time
from contextlib import contextmanager
from typing import Iterator, List, Optional, Self, Type

from fastapi.testclient import TestClient
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.message import Message
from httpx import Response
from pydantic import BaseModel


class GcpPubsubPushEmulator[T: BaseModel]:
    _log = logging.getLogger(__name__)

    def __init__(self, subscription_path: str, clazz: Optional[Type[T]] = None):
        self.subscription_path = subscription_path
        self.clazz = clazz
        self.messages: List[Message] = []
        self.payloads: List[T] = []
        self.responses: List[Response] = []
        self.start_time = time.time()

    @contextmanager
    def run_push_emulator(self, client: TestClient, endpoint_url: str) -> Iterator[Self]:
        """
        A context manager that simulates a Pub/Sub push subscription.

        It listens for messages on the given subscription and POSTs them to the
        specified HTTP endpoint using a FastAPI TestClient. This is useful for
        integration testing of push-based Pub/Sub endpoints.
        """
        from .gcp_pubsub_model import GcpPubsubRequest

        subscriber = pubsub_v1.SubscriberClient()

        def callback(message: Message) -> None:
            try:
                self.messages.append(message)
                if self.clazz:
                    self.payloads.append(self.clazz.model_validate_json(message.data.decode("utf-8")))
                response = client.post(endpoint_url, json=GcpPubsubRequest.create_from_message(message).model_dump())
                self.responses.append(response)
                if response.status_code != 200:
                    self._log.error("Failed to deliver message %s: %s", message.message_id, response.text)
                else:
                    self._log.info("Successfully delivered message %s", message.message_id)
            except Exception as exc:
                self._log.exception(f"Exception during message delivery: {exc}")
            finally:
                message.ack()

        streaming_pull_future = subscriber.subscribe(self.subscription_path, callback=callback)
        with subscriber:
            try:
                self.responses = []
                self.start_time = time.time()
                yield self
            finally:
                streaming_pull_future.cancel()
                try:
                    streaming_pull_future.result(timeout=5)
                except Exception:
                    pass

    def isfinished(self, timeout: float = 60.0, expected_responses: int = 1) -> bool:
        if time.time() >= self.start_time + timeout:
            self._log.error("Timeout while waiting for responses")
            return True
        if len(self.responses) >= expected_responses:
            self._log.info("All responses received")
            return True
        return False

    def get_responses(self) -> List[Response]:
        return self.responses

    def get_messages(self) -> List[Message]:
        return self.messages

    def get_payloads(self) -> List[T]:
        return self.payloads
