import uuid

import pytest

from ampf.gcp.gcp_topic import GcpTopic


@pytest.fixture(scope="session")
def topic():
    topic_id = "ampf_unit_tests_" + uuid.uuid4().hex[:6]
    topic = GcpTopic(topic_id).create(exist_ok=True)
    yield topic
    topic.delete()


@pytest.fixture(scope="session")
def subscription(topic: GcpTopic):
    subscription = topic.create_subscription(exist_ok=True)
    yield subscription
    subscription.delete()
