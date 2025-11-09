import logging
import os
from abc import ABC
from typing import Optional, Self

from google.api_core.exceptions import AlreadyExists, DeadlineExceeded, NotFound
from google.cloud.pubsub_v1 import SubscriberClient
from pydantic import BaseModel
import asyncio



class GcpBaseSubscription[T: BaseModel](ABC):
    """A base class for GCP Pub/Sub subscriptions."""

    _log = logging.getLogger(__name__)

    def __init__(
        self,
        subscription_id: str,
        project_id: Optional[str] = None,
        subscriber: Optional[SubscriberClient] = None,
    ):
        """Initializes the subscription.

        Args:
            subscription_id: The name of the subscription.
            project_id: The project ID.
            clazz: The class to which the message data should be deserialized.
            subscriber: The subscriber client.
        """
        self.subscription_id = subscription_id
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not self.project_id:
            raise ValueError("Project ID or GOOGLE_CLOUD_PROJECT environment variable is not set")
        self.subscriber = subscriber or SubscriberClient()

        self.subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_id)

    def exists(self) -> bool:
        """Checks if the subscription exists in GCP.

        Returns:
            True if the subscription exists, False otherwise.
        """
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
                ack_deadline_seconds=600,
            )
        except AlreadyExists as e:
            if not exist_ok:
                raise e
        return self

    def delete(self) -> None:
        """Deletes the subscription in GCP."""
        self.subscriber.delete_subscription(subscription=self.subscription_path)

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

    async def wait_until_empty(self, timeout: float = 5.0, check_interval: float = 1.0) -> None:
        """Waits until the subscription is empty or the timeout is reached.
        Args:
            time_out: The maximum time to wait in seconds.
            check_interval: The interval between checks in seconds.
        """
        total_waited = 0.0
        while total_waited < timeout and not self.is_empty():
            await asyncio.sleep(check_interval)
            total_waited += check_interval
        assert self.is_empty(), "Subscription is not empty after waiting"

    def clear(self):
        """Clears the subscription of all messages."""
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
