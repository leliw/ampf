import logging
from typing import Dict, Optional, Type

import pytest
from pydantic import BaseModel


# Flag to check if GCP dependencies are installed.
GCP_INSTALLED = False
try:
    from ampf.gcp import GcpSubscription, GcpTopic

    GCP_INSTALLED = True
except ImportError:
    pass  # GCP dependencies are not installed, GcpSubscription and GcpTopic will not be available.
if GCP_INSTALLED:
    class PubSubManager:
        """A manager for GCP Pub/Sub topics and subscriptions."""

        _log = logging.getLogger(__name__)

        def __init__(self):
            self.topics: Dict[str, GcpTopic] = {}
            self.subscriptions: Dict[str, GcpSubscription] = {}

        def prepare_topic[T: BaseModel](self, topic_id: str, clazz: Optional[Type[T]] = None) -> GcpTopic[T]:
            """Prepares a GCP Pub/Sub topic. If it does not exist, it is created.

            Args:
                topic_id: The ID of the topic.
                clazz: The Pydantic model class for the topic's messages.
            Returns:
                GcpTopic[T]: The prepared GCP Pub/Sub topic.
            """
            if topic_id in self.topics:
                return self.topics[topic_id]
            topic = GcpTopic[T](topic_id)
            if not topic.exists():
                topic.create()
                self.topics[topic_id] = topic
                self._log.info("Created topic: %s", topic.topic_path)
            return topic

        def prepare_subscription[T: BaseModel](
            self, subcription_id: str, clazz: Optional[Type[T]] = None, topic_id: Optional[str] = None
        ) -> GcpSubscription[T]:
            """Prepares a GCP Pub/Sub subscription. If it does not exist, it is created.

            Args:
                subcription_id: The ID of the subscription.
                clazz: The Pydantic model class for the subscription's messages.
                topic_id: The ID of the topic to subscribe to. If None, it is inferred  from the subscription ID.
            Returns:
                GcpSubscription[T]: The prepared GCP Pub/Sub subscription.
            """
            if subcription_id in self.subscriptions:
                return self.subscriptions[subcription_id]
            if topic_id is None and subcription_id.endswith("-sub"):
                topic_id = subcription_id[: -len("-sub")]
            elif topic_id is None:
                raise ValueError("topic_id must be provided if subscription_id does not end with '-sub'")
            topic = self.prepare_topic(topic_id, clazz)
            subscription = GcpSubscription(subcription_id, clazz=clazz)
            if not subscription.exists():
                subscription = topic.create_subscription(
                    subcription_id,
                    clazz=clazz,
                    processing_timeout=60.0,
                    per_message_timeout=1.0,
                    exist_ok=True,
                )
                self.subscriptions[subcription_id] = subscription
                self._log.info("Created subscription: %s", subscription.subscription_id)
            else:
                subscription.clear()
            return subscription

        def prepare_resources(self, config: BaseModel):
            """Prepares all topics and subscriptions defined in the given config.

            Topics and subscriptions are identified by field names ending with
            "_topic" and "_subscription", respectively.

            Args:
                config: The config object containing the topics and subscriptions.
            """
            for field_name in config.model_fields_set:
                if field_name.endswith("_topic"):
                    topic_id = getattr(config, field_name)
                    self.prepare_topic(topic_id)
                elif field_name.endswith("_subscription"):
                    subscription_id = getattr(config, field_name)
                    topic_field_name = field_name[: -len("_subscription")] + "_topic"
                    topic_id = getattr(config, topic_field_name, None)
                    self.prepare_subscription(subscription_id, topic_id=topic_id)

        def publish(self, topic_id: str, data: BaseModel) -> None:
            """Publishes a message to the specified topic.

            Args:
                topic_id: The ID of the topic to publish to.
                data: The message to publish.
            """
            topic = self.prepare_topic(topic_id, type(data))
            topic.publish(data)

        async def wait_until_empty(self, subscription_id: str, timeout: float = 10.0) -> None:
            """Waits until the specified subscription is empty or the timeout is reached.

            Args:
                subscription_id: The ID of the subscription to wait for.
                timeout: The maximum time to wait for the subscription to be empty.
            """
            subscription = self.prepare_subscription(subscription_id)
            await subscription.wait_until_empty(timeout=timeout)

        def cleanup(self):
            """
            Deletes all topics and subscriptions created by this factory.
            """
            for subscription in self.subscriptions.values():
                subscription.delete()
                self._log.info("Deleted subscription: %s", subscription.subscription_id)
            for topic in self.topics.values():
                topic.delete()
                self._log.info("Deleted topic: %s", topic.topic_path)


    @pytest.fixture(scope="session")
    def pubsub_manager() -> PubSubManager:  # type: ignore
        factory = PubSubManager()
        yield factory  # type: ignore
        factory.cleanup()
else:
    @pytest.fixture(scope="session")
    def pubsub_manager():
        raise RuntimeError("ampf[gcp] is not installed")
