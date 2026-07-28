import pytest

from ampf.base.base_subscription import BaseSubscription
from ampf.base.base_topic import BaseTopic
from ampf.in_memory.in_memory_factory import InMemoryFactory
from ampf.in_memory.pubsub.in_memory_registry import MemoryPubsubRegistry

topic_id = "xxx"


@pytest.fixture
def factory():
    MemoryPubsubRegistry.reset()
    return InMemoryFactory()

def test_create_topic(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # Where: A topic is created
    topic = factory.create_topic(topic_id)
    # Then: A BaseTopic subclas is returned
    assert isinstance(topic, BaseTopic)


def test_create_topic_and_subscription(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # And: A topic
    topic = factory.create_topic(topic_id)
    # When: A subscription is created
    subscription = topic.create_subscription()
    # Then: A BaseTopic subclass is returned
    assert isinstance(subscription, BaseSubscription)

def test_receive_empty_queue(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # And: A topic and subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription()
    # When: The message is received from the empty queue
    received_message = subscription.receive_message(timeout=1.0)
    # Then: The received message is None
    assert received_message is None

def test_publish_and_receive(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # And: A topic and subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription()
    # When: A message is published via topic
    message_id = topic.publish("Hello, World!", attrs={"key": "value"})
    # Then: The message can be received via subscription
    received_message = subscription.receive_message(timeout=1.0)
    assert received_message is not None
    assert received_message.messageId == message_id
    assert received_message.data == "Hello, World!"
    assert received_message.attributes
    assert received_message.attributes["key"] == "value"
