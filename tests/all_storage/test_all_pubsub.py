import pytest

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

def test_create_topic_and_subscription(factory: BaseFactory):
    # Given: A factory
    assert factory
    # And: A topic
    topic = factory.create_topic(topic_id)
    # When: A subscription is created
    subscription = topic.create_subscription()
    # Then: A BaseTopic subclas is returned
    assert isinstance(subscription, BaseSubscription)
