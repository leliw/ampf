import uuid

import pytest

from ampf.gcp.gcp_topic import GcpTopic
from ampf.testing import mock_method  # noqa: F401


@pytest.fixture(scope="session")
def existing_topic():
    topic = GcpTopic(topic_id="ampf_unit_tests_existing_topic")
    topic.create(exist_ok=True)
    yield topic
    topic.delete()


@pytest.fixture(scope="session")
def existing_subscription(existing_topic: GcpTopic):
    subscription = existing_topic.create_subscription(exist_ok=True)
    yield subscription
    subscription.delete()


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


@pytest.fixture(scope="session")
def topic2():
    topic_id = "ampf_unit_tests_" + uuid.uuid4().hex[:6]
    topic = GcpTopic(topic_id).create(exist_ok=True)
    yield topic
    topic.delete()


@pytest.fixture(scope="session")
def subscription2(topic2: GcpTopic):
    subscription = topic2.create_subscription(exist_ok=True)
    yield subscription
    subscription.delete()
