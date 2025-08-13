from contextlib import contextmanager
import logging
import os
import queue
import subprocess
import time
from concurrent.futures import TimeoutError
from typing import Callable, Generator, Iterator, Optional, Self, Type

from google.cloud import pubsub_v1
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

    def receive_messages(self) -> Generator[Message, None, None]:
        """Receives messages from the subscription.

        Yields:
            The received messages.
        """
        _messages_queue = queue.Queue()
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(self.project_id, self.subscription_id)

        def callback(message: Message) -> None:
            _messages_queue.put(message)
            message.ack()

        streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

        with subscriber:
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

    def create(self, topic_id: str, exist_ok: bool = False) -> Self:
        """Creates the subscription in GCP if it does not exist.

        Args:
            topic_id: The ID of the topic to subscribe to.
            exist_ok: If True, no exception is raised if the subscription already exists.
        Returns:
            The subscription itself.
        """
        ret = subprocess.run(
            ["gcloud", "pubsub", "subscriptions", "create", self.subscription_id, "--topic", topic_id],
            capture_output=True,
            text=True,
        )
        if ret.returncode != 0:
            if not exist_ok or "already exists" not in ret.stderr:
                self._log.error(ret.stderr)
                raise subprocess.CalledProcessError(ret.returncode, ret.args, ret.stdout, ret.stderr)
        return self

    def delete(self) -> None:
        """Deletes the subscription in GCP."""
        subprocess.run(
            ["gcloud", "pubsub", "subscriptions", "delete", self.subscription_id],
            capture_output=True,
            text=True,
        ).check_returncode()

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
            subscription_path = pubsub_v1.SubscriberClient.subscription_path(self.project_id, self.subscription_id)
            emulator = GcpPubsubPushEmulator[T](subscription_path, self.clazz)
            with emulator.run_push_emulator(client, endpoint_url) as sub_emulator:
                yield sub_emulator

    except ImportError:
        pass