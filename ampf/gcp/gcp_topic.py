import logging
import os
import subprocess
from typing import Dict, Optional, Self, Type

from google.cloud import pubsub_v1
from pydantic import BaseModel

from ampf.gcp.gcp_subscription import GcpSubscription


class GcpTopic[T: BaseModel]:
    _log = logging.getLogger(__name__)

    def __init__(self, topic_id: str, project_id: Optional[str] = None):
        """Initializes the topic.

        Args:
            topic_id: The name of the topic.
            project_id: The project ID.
        """
        self.topic_id = topic_id
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("Project ID or GOOGLE_CLOUD_PROJECT environment variable is not set")
        self.publisher = pubsub_v1.PublisherClient()
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
            future = self.publisher.publish(self.topic_path, bdata, **attrs)
        else:
            future = self.publisher.publish(self.topic_path, bdata)
        return future.result()

    def create(self, exist_ok: bool = False) -> Self:
        """Creates the topic in GCP if it does not exist.

        Args:
            exist_ok: If True, no exception is raised if the topic already exists.
        Returns:
            The topic itself.
        """
        ret = subprocess.run(
            ["gcloud", "pubsub", "topics", "create", self.topic_id],
            capture_output=True,
            text=True,
        )
        if ret.returncode != 0:
            if not exist_ok or "already exists" not in ret.stderr:
                self._log.error(ret.stderr)
                raise subprocess.CalledProcessError(ret.returncode, ret.args, ret.stdout, ret.stderr)
        return self

    def delete(self) -> None:
        """Deletes the topic in GCP."""
        subprocess.run(
            ["gcloud", "pubsub", "topics", "delete", self.topic_id],
            capture_output=True,
            text=True,
        ).check_returncode()

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
