import logging
import os
from typing import Dict, Optional, Self, Type

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud.pubsub_v1 import PublisherClient
from pydantic import BaseModel

from ampf.gcp.gcp_subscription import GcpSubscription


class GcpTopic[T: BaseModel]:
    _log = logging.getLogger(__name__)
    _default_publisher: Optional[PublisherClient] = None

    @classmethod
    def get_default_publisher(cls) -> PublisherClient:
        if cls._default_publisher is None:
            cls._default_publisher = PublisherClient()
        return cls._default_publisher

    def __init__(self, topic_id: str, project_id: Optional[str] = None, publisher: Optional[PublisherClient] = None):
        """Initializes the topic.

        Args:
            topic_id: The name of the topic.
            project_id: The project ID.
        """
        self.topic_id = topic_id
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("Project ID or GOOGLE_CLOUD_PROJECT environment variable is not set")
        self.publisher = publisher or self.get_default_publisher()
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)

    def publish(
        self,
        data: T | str | bytes,
        attrs: Optional[Dict[str, str]] = None,
        response_topic: Optional[str] = None,
        sender_id: Optional[str] = None,
    ) -> str:
        """Publishes a message to the topic.

        Args:
            data: The message to publish.
            attrs: The attributes of the message.
        Returns:
            The message ID.
        """
        if response_topic:
            attrs = attrs or {}
            attrs["response_topic"] = response_topic
        if sender_id:
            attrs = attrs or {}
            attrs["sender_id"] = sender_id
        if isinstance(data, str):
            bdata = data.encode("utf-8")
        elif isinstance(data, bytes):
            bdata = data
        elif isinstance(data, BaseModel):
            bdata = data.model_dump_json().encode("utf-8")
        else:
            raise ValueError("Unsupported data type")
        # When you publish a message, the client returns a future.
        if attrs:
            self._log.debug("Publishing message in topic %s with attributes: %s", self.topic_id, attrs)
            future = self.publisher.publish(self.topic_path, bdata, **attrs)
        else:
            self._log.debug("Publishing message in topic %s", self.topic_id)
            future = self.publisher.publish(self.topic_path, bdata)
        return future.result()

    def exists(self) -> bool:
        try:
            self.publisher.get_topic(topic=self.topic_path)
            return True
        except NotFound:
            return False

    def create(self, exist_ok: bool = False) -> Self:
        """Creates the topic in GCP if it does not exist.

        Args:
            exist_ok: If True, no exception is raised if the topic already exists.
        Returns:
            The topic itself.
        """
        try:
            self.publisher.create_topic(name=self.topic_path)
        except AlreadyExists as e:
            if not exist_ok:
                raise e
        return self

    def delete(self) -> None:
        """Deletes the topic in GCP."""
        self.publisher.delete_topic(topic=self.topic_path)

    def create_subscription[R: BaseModel](
        self,
        subscription_id: Optional[str] = None,
        clazz: Optional[Type[R]] = None,
        processing_timeout: float = 5.0,
        per_message_timeout: float = 1.0,
        exist_ok: bool = False,
    ) -> GcpSubscription[R]:
        """Creates a subscription to the topic in GCP.

        Args:
            subscription_id: The ID of the subscription.
            clazz: The class to which the message data should be deserialized.
            processing_timeout: The maximum time in seconds to process messages.
            per_message_timeout: The maximum time in seconds to wait for a single message.
            exist_ok: If True, no exception is raised if the subscription already exists.
        Returns:
            The created GcpSubscription object.
        """
        subscription_id = subscription_id or f"{self.topic_id}-sub"
        subscription = GcpSubscription(
            subscription_id=subscription_id,
            project_id=self.project_id,
            clazz=clazz,
            processing_timeout=processing_timeout,
            per_message_timeout=per_message_timeout,
        )
        subscription.create(self.topic_id, exist_ok=exist_ok)
        return subscription
