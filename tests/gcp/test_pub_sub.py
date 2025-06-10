import time

import pytest
from pydantic import BaseModel

from ampf.gcp import GcpSubscription, GcpTopic

# gcloud pubsub topics create unit-tests
# gcloud pubsub subscriptions create unit-tests-sub --topic unit-tests


class D(BaseModel):
    name: str


def test_basic_pub_sub():
    # Given: project_id, topic_id, subscription_id
    project_id = "development-428212"
    topic_id = "unit-tests"
    subscription_id = "unit-tests-sub"
    # When: Topic is created
    topic = GcpTopic(project_id, topic_id)
    # And: Subscription is created
    subscription = GcpSubscription(
        project_id, subscription_id, D, processing_timeout=5.0, per_message_timeout=1.0
    )
    # And: Message is published
    data = D(name=f"Test message {time.time()}")
    topic.publish(data)

    # And: Message is received
    received_messages = []
    try:
        for msg_data in subscription:
            received_messages.append(msg_data)
            if msg_data == data:
                break
    except Exception as e:
        pytest.fail(f"Generator subskrypcji zgłosił wyjątek: {e}")

    # Then: Message is received
    assert data in received_messages, (
        f"Wiadomość '{data}' nie została znaleziona w {received_messages}"
    )
