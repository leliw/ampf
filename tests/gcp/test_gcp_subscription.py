from uuid import uuid4

import pytest
from google.api_core.exceptions import AlreadyExists

from ampf.gcp.gcp_subscription import GcpSubscription


def test_create_not_existing(existing_topic):
    # Given: Existing topic and subscription object
    subscr = GcpSubscription(subscription_id="ampf_unit_tests_" + uuid4().hex[:6])
    # When: Create subscription
    subscr.create(existing_topic.topic_id, exist_ok=False)
    # Then: Subscription exists
    assert subscr.exists()
    # Clean up
    subscr.delete()


def test_create_existing_error(existing_topic, existing_subscription):
    # Given: Existing subscription
    # When: Create subscription
    # Then: Exception is raised
    with pytest.raises(AlreadyExists):
        existing_subscription.create(existing_topic.topic_id, exist_ok=False)


def test_create_existing_OK(existing_topic, existing_subscription):
    # Given: Existing subscription
    # When: Create subscription with exists_ok = True
    existing_subscription.create(existing_topic.topic_id, exist_ok=True)
    # Then: Exception is NOT raised
    assert True


def test_not_exists():
    # Given: Existing topic and subscription object
    subscr = GcpSubscription(subscription_id="ampf_unit_tests_" + uuid4().hex[:6])
    # When: Check if exists
    result = subscr.exists()
    # Then: Return false
    assert not result


def test_exists(existing_subscription):
    # Given: Existing subscription
    # When: Check if exists
    result = existing_subscription.exists()
    # Then: Return true
    assert result


def test_is_not_empty(existing_topic, existing_subscription):
    # Given: Existing topic & subscription
    # And: A message is sent
    existing_topic.publish("test")
    # When: Check if is_empty
    # Then: Return false
    assert not existing_subscription.is_empty()
    # Clean up
    existing_subscription.clear()


def test_is_empty(existing_subscription):
    # Given: Existing topic & subscription
    # When: Check if is_empty
    # Then: Return true
    assert existing_subscription.is_empty()


def test_clear(existing_topic, existing_subscription):
    # Given: Existing topic & subscription
    # And: A message is sent
    existing_topic.publish("test")
    assert not existing_subscription.is_empty()
    # When: Subscription is cleared
    existing_subscription.clear()
    # Then: Subscription is empty
    assert existing_subscription.is_empty()
