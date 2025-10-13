import logging
from typing import Optional, Type
from uuid import uuid4

import pytest
from ampf.gcp import GcpSubscription, GcpTopic
from pydantic import BaseModel

_log = logging.getLogger(__name__)


class SubscriptionFactory:
    """
    A factory for creating GCP Pub/Sub topics and subscriptions.
    """

    def __init__(self):
        self.topics = []
        self.subscriptions = []

    def __call__[T: BaseModel](
        self, topic_name: str, clazz: Type[T], subcription_name: Optional[str] = None
    ) -> GcpSubscription[T]:
        """
        Creates a GCP Pub/Sub topic and a subscription to it.

        Args:
            topic_name (str): The name of the topic.
            clazz (Type[T]): The Pydantic model class for the subscription's messages.
            subcription_name (Optional[str]): The name of the subscription. If not provided, a unique name will be generated.
        Returns:
            GcpSubscription[T]: The created GCP Pub/Sub subscription.
        """
        subcription_name = subcription_name or f"{topic_name}-sub-" + uuid4().hex
        topic = GcpTopic(topic_name)
        if not topic.exists():
            topic.create(exist_ok=True)
            self.topics.append(topic)
            _log.debug("Created topic: %s", topic.topic_path)
        subscription = GcpSubscription(subcription_name, clazz=clazz)
        if not subscription.exists():
            subscription = topic.create_subscription(
                subcription_name,
                clazz=clazz,
                processing_timeout=60.0,
                per_message_timeout=1.0,
                exist_ok=True,
            )
            self.subscriptions.append(subscription)
        else:
            subscription.clear()
        return subscription

    def cleanup(self):
        """
        Deletes all topics and subscriptions created by this factory.
        """
        for subscription in self.subscriptions:
            subscription.delete()
            _log.info("Deleted subscription: %s", subscription.subscription_id)
        for topic in self.topics:
            topic.delete()
            _log.info("Deleted topic: %s", topic.topic_path)


@pytest.fixture(scope="package")
def subscription_factory() -> SubscriptionFactory:  # type: ignore
    """
    Fixture that provides a factory for creating GCP Pub/Sub subscriptions
    and ensures their cleanup after tests.
    """
    factory = SubscriptionFactory()
    yield factory  # type: ignore
    factory.cleanup()


# @pytest.fixture(scope="package")
# def subscription_factory[T: BaseModel]() -> Callable[[str, Type[T]], GcpSubscription[T]]: # type: ignore
#     topics = []
#     subscriptions = []

#     def _subscription_factory(topic_name: str, clazz: Type[T]) -> GcpSubscription[T]:
#         topic = GcpTopic(topic_name)
#         topic.create(exist_ok=True)
#         _log.info("Created topic: %s", topic.topic_path)
#         subscription = topic.create_subscription(
#             f"{topic.topic_id}-sub",
#             clazz=clazz,
#             processing_timeout=60.0,
#             per_message_timeout=1.0,
#             exist_ok=True,
#         )
#         _log.info("Created subscription: %s", subscription.subscription_id)
#         topics.append(topic)
#         subscriptions.append(subscription)
#         return subscription

#     yield _subscription_factory # type: ignore

#     for subscription in subscriptions:
#             subscription.delete()
#             _log.info("Deleted subscription: %s", subscription.subscription_id)
#     for topic in topics:
#         topic.delete()
#         _log.info("Deleted topic: %s", topic.topic_path)
