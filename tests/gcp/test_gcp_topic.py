from uuid import uuid4

import pytest

from ampf.gcp.gcp_topic import AlreadyExists, GcpTopic


@pytest.fixture(scope="session")
def existing_topic():
    topic = GcpTopic(topic_id="ampf_unit_tests_existing_topic")
    topic.create(exist_ok=True)
    yield topic
    topic.delete()


def test_create_not_existing():
    # Given: Not existing topic_id
    topic = GcpTopic(topic_id="ampf_unit_tests_" + uuid4().hex[:6])
    # When: Create topic
    topic.create(exist_ok=False)
    # Then: Topic exists
    assert topic.exists()
    # Clean up
    topic.delete()


def test_create_existing_error(existing_topic):
    # Given: Existing topic
    # When: Create topic
    # Then: Exception is raised
    with pytest.raises(AlreadyExists):
        existing_topic.create(exist_ok=False)

def test_create_existing_ok(existing_topic):
    # Given: Existing topic
    # When: Create topic with exists_ok = True
    existing_topic.create(exist_ok=True)
    # Then: No exception raised
    assert True


def test_not_exists():
    # Given: Not existing topic_id
    topic = GcpTopic(topic_id="ampf_unit_tests_" + uuid4().hex[:6])
    # When: Check if exists
    result = topic.exists()
    # Then: Return false
    assert not result


def test_exists(existing_topic):
    # Given: Existing topic
    # When: Check if exists
    result = existing_topic.exists()
    # Then: Return true
    assert result

def test_delete():
    # Given: Created topic
    topic = GcpTopic(topic_id="ampf_unit_tests_" + uuid4().hex[:6])
    topic.create()
    # When: Delete
    topic.delete()
    # Then: Topic does not exist
    assert not topic.exists()
