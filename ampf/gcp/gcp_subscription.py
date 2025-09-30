import logging
import os
import queue
import time
from concurrent.futures import TimeoutError
from contextlib import contextmanager
from typing import Callable, Generator, Iterator, Optional, Self, Type

from google.api_core.exceptions import AlreadyExists, DeadlineExceeded, NotFound
from google.cloud.pubsub_v1 import SubscriberClient
from google.cloud.pubsub_v1.subscriber.message import Message
from pydantic import BaseModel

from ampf.gcp.gcp_pubsub_push_emulator import GcpPubsubPushEmulator


class GcpSubscription[T: BaseModel]:
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        subscription_id: str,
        project_id: Optional[str] = None,
        clazz: Optional[Type[T]] = None,
        processing_timeout: float = 5.0,
        per_message_timeout: float = 1.0,
        subscriber: Optional[SubscriberClient] = None,
    ):
        """Initializes the subscription.

        Args:
            subscription_id: The name of the subscription.
            project_id: The project ID.
            clazz: The class to which the message data should be deserialized.
            processing_timeout: The maximum time in seconds to process messages.
            per_message_timeout: The maximum time in seconds to wait for a single message.
        """
        self.subscription_id = subscription_id
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not self.project_id:
            raise ValueError("Project ID or GOOGLE_CLOUD_PROJECT environment variable is not set")
        self.clazz = clazz
        self.processing_timeout = processing_timeout
        self.per_message_timeout = per_message_timeout
        self.subscriber = subscriber or SubscriberClient()

        self.subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_id)

    def receive_messages(self) -> Generator[Message, None, None]:
        """Receives messages from the subscription.

        Yields:
            The received messages.
        """
        _messages_queue = queue.Queue()

        def callback(message: Message) -> None:
            _messages_queue.put(message)
            message.ack()

        streaming_pull_future = self.subscriber.subscribe(self.subscription_path, callback=callback)

        end_time = time.time() + self.processing_timeout
        try:
            while time.time() < end_time:
                try:
                    remaining_time_for_cycle = end_time - time.time()
                    if remaining_time_for_cycle <= 0:
                        break
                    current_wait_timeout = min(self.per_message_timeout, remaining_time_for_cycle)
                    message = _messages_queue.get(block=True, timeout=current_wait_timeout)
                    yield message
                except queue.Empty:
                    if not streaming_pull_future.running():
                        break
                    continue
        finally:
            if streaming_pull_future.running():
                streaming_pull_future.cancel()
                try:
                    streaming_pull_future.result(timeout=2.0)
                except TimeoutError:
                    pass
                except Exception:
                    pass

    def __iter__(self) -> Generator[T, None, None]:
        """Iterates over the messages in the subscription.

        Yields:
            The deserialized messages.
        """
        for message in self.receive_messages():
            if self.clazz:
                yield self.clazz.model_validate_json(message.data.decode("utf-8"))
            else:
                raise TypeError(
                    "clazz is not set, so cannot deserialize message. Set clazz in the constructor to deserialize messages."
                )

    def exists(self) -> bool:
        try:
            self.subscriber.get_subscription(subscription=self.subscription_path)
            return True
        except NotFound:
            return False

    def create(self, topic_id: str, exist_ok: bool = False) -> Self:
        """Creates the subscription in GCP if it does not exist.

        Args:
            topic_id: The ID of the topic to subscribe to.
            exist_ok: If True, no exception is raised if the subscription already exists.
        Returns:
            The subscription itself.
        """
        try:
            self.subscriber.create_subscription(
                name=self.subscription_path,
                topic=self.subscriber.topic_path(self.project_id, topic_id),
            )
        except AlreadyExists as e:
            if not exist_ok:
                raise e
        return self

    def delete(self) -> None:
        """Deletes the subscription in GCP."""
        self.subscriber.delete_subscription(subscription=self.subscription_path)

    def receive_first_message(self, filter: Callable[[Message], bool]) -> Optional[Message]:
        """Receives the first message that satisfies the filter.

        Args:
            filter: A callable that takes a message and returns True if the message satisfies the filter.
        Returns:
            The first message that satisfies the filter, or None if no such message is received within the timeout.
        """
        for message in self.receive_messages():
            if filter(message):
                return message

    def receive_first_payload(self, filter: Callable[[T], bool]) -> Optional[T]:
        """Receives the first message **payload** that satisfies the filter.

        Args:
            filter: A callable that takes a message data and returns True if the payload satisfies the filter.
        Returns:
            The first payload that satisfies the filter, or None if no such message is received within the timeout.
        """
        for payload in self:
            if filter(payload):
                return payload

    try:
        from fastapi.testclient import TestClient

        @contextmanager
        def run_push_emulator(self, client: TestClient, endpoint_url: str) -> Iterator[GcpPubsubPushEmulator[T]]:
            emulator = GcpPubsubPushEmulator[T](self.subscription_path, self.clazz)
            with emulator.run_push_emulator(client, endpoint_url) as sub_emulator:
                yield sub_emulator

    except ImportError:
        pass

    def is_empty(self) -> bool:
        """Checks if the subscription is empty.

        Returns:
            True if the subscription is empty, False otherwise.
        """
        try:
            response = self.subscriber.pull(
                subscription=self.subscription_path, max_messages=1, return_immediately=True
            )
            return not response.received_messages
        except Exception:
            return True

    def clear(self):
        while True:
            try:
                response = self.subscriber.pull(subscription=self.subscription_path, max_messages=1000, timeout=1.0)
            except DeadlineExceeded:
                break
            if not response.received_messages:
                break
            ack_ids = [m.ack_id for m in response.received_messages]
            if ack_ids:
                self.subscriber.acknowledge(subscription=self.subscription_path, ack_ids=ack_ids)
