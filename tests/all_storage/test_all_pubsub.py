import pytest
from pydantic import BaseModel

from ampf.base.base_factory import BaseFactory
from ampf.base.base_subscription import BaseSubscription
from ampf.base.base_topic import BaseTopic
from ampf.gcp.gcp_factory import GcpFactory
from ampf.in_memory.in_memory_factory import InMemoryFactory

topic_id = "it-ampf-topic-1"

@pytest.fixture(params=[InMemoryFactory, GcpFactory])
def factory(request):
    if request.param == GcpFactory:
        factory = request.param(bucket_name="unit-tests-001")
    else:
        factory = request.param()
    return factory


def test_create_topic(factory: BaseFactory):
    # Given: A factory
    assert factory
    # Where: A topic is created
    topic = factory.create_topic(topic_id)
    # Then: A BaseTopic subclass is returned
    assert isinstance(topic, BaseTopic)
    # And: Topic_id is stored
    assert topic.topic_id == topic_id

def test_create_topic_and_subscription(factory: BaseFactory):
    # Given: A factory
    assert factory
    # And: A topic
    topic = factory.create_topic(topic_id)
    # When: A subscription is created
    subscription = topic.create_subscription()
    # Then: A BaseTopic subclass is returned
    assert isinstance(subscription, BaseSubscription)

# def test_publish_and_receive_str(factory: BaseFactory):
#     # Given: A topic & a subscription
#     topic = factory.create_topic(topic_id)
#     subscription = topic.create_subscription()
#     # When: Publish a string
#     payload = "Hello!"
#     message_id = topic.publish(payload)
#     # And: receive it
#     message = subscription.receive_message()
#     # Then: They are the same
#     assert message
#     assert message.messageId == message_id
#     assert payload == message.data

class C(BaseModel):
    name: str

def test_publish_and_receive(factory: BaseFactory):
    # Given: A topic & a subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription()
    # And: A payload
    payload = C(name="XXX")
    # When: Publish message
    message_id = topic.publish(payload)
    # And: receive it
    message = subscription.receive_message()
    # Then: They are the same
    assert message
    assert message.messageId == message_id
    assert payload == message.decoded_data(C)
