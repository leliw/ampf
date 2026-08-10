import queue
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager

from pydantic import BaseModel

from ampf.base.base_push_emulator import BasePushEmulator
from ampf.base.base_subscription import BaseSubscription

from ...shared.pubsub_message import PubsubMessage
from .in_memory_registry import InMemoryPubsubRegistry


class InMemorySubscription[T: BaseModel](BaseSubscription):
    """Subskrypcja w pamięci (generatorowa) do testów jednostkowych."""

    def __init__(
        self,
        pubsub_registry: InMemoryPubsubRegistry, 
        subscription_id: str,
        topic=None,
        clazz: type[T] | None = None,
        processing_timeout: float = 5.0,
        per_message_timeout: float = 1.0,
    ):
        self.pubsub_registry = pubsub_registry
        self.subscription_id = subscription_id
        self.topic = topic
        self.clazz = clazz
        self.processing_timeout = processing_timeout
        self.per_message_timeout = per_message_timeout
        self._queue = queue.Queue()
        self.pubsub_registry.register_subscription(self)

    def put_message(self, message: PubsubMessage):
        self._queue.put(message)

    def receive_message(self, timeout: float | None = None) -> PubsubMessage | None:
        try:
            return self._queue.get(block=True, timeout=timeout)
        except queue.Empty:
            return None

    def receive_messages(
        self,
        processing_timeout: float | None = None,
        per_message_timeout: float | None = None,
    ) -> Generator[PubsubMessage]:
        """Generator that yields messages from the subscription's queue."""
        processing_timeout = processing_timeout or self.processing_timeout
        per_message_timeout = per_message_timeout or self.per_message_timeout
        end_time = time.time() + processing_timeout
        while time.time() < end_time:
            remaining_time = end_time - time.time()
            if remaining_time <= 0:
                break
            current_wait_timeout = min(per_message_timeout, remaining_time)
            message = self.receive_message(timeout=current_wait_timeout)
            if message is not None:
                yield message

    def __iter__(self) -> Generator[T]:
        for message in self.receive_messages():
            if self.clazz:
                yield message.decoded_data(self.clazz)
            else:
                raise TypeError("clazz is not set, so cannot deserialize message.")

    def receive_first_message(self, filter: Callable[[PubsubMessage], bool]) -> PubsubMessage | None:
        for message in self.receive_messages():
            if filter(message):
                return message
        return None

    def receive_first_payload(self, filter: Callable[[T], bool] | None = None) -> T | None:
        for payload in self:
            if not filter or filter(payload):
                return payload
        return None

    def create(self, topic_id: str, exist_ok: bool = False) -> None:
        self.pubsub_registry.bind(self.subscription_id, topic_id)

    def delete(self) -> None:
        self.pubsub_registry.delete(self.subscription_id)

    try:
        from fastapi.testclient import TestClient

        @contextmanager
        def run_push_emulator(self, client: TestClient, endpoint_url: str):
            emulator = BasePushEmulator(self, self.clazz)
            with emulator.run_push_emulator(client, endpoint_url) as emu:
                yield emu
    except ImportError:
        pass
