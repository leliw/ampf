import time

import pytest
from pydantic import BaseModel

from ampf.gcp import GcpSubscription, GcpTopic


class D(BaseModel):
    name: str


def test_basic_pub_sub(topic: GcpTopic, subscription: GcpSubscription):
    # Given: A topic and a typed subscription
    typed_subscription = GcpSubscription(subscription.subscription_id, subscription.project_id, D)
    # When: Message is published
    data = D(name=f"Test message {time.time()}")
    topic.publish(data)
    # Then: Message is received
    received_messages = []
    try:
        for msg_data in typed_subscription:
            received_messages.append(msg_data)
            if msg_data == data:
                break
    except Exception as e:
        pytest.fail(f"Generator subskrypcji zgłosił wyjątek: {e}")
    assert data in received_messages, f"Wiadomość '{data}' nie została znaleziona w {received_messages}"


def test_pub_sub_with_attrs(topic: GcpTopic, subscription: GcpSubscription):
    # Given: A topic and a subscription
    # When: Message is published with attrs
    data = D(name=f"Test message {time.time()}")
    topic.publish(data, {"a": "b"})
    # Then: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["a"] == "b")
    assert received_message
    assert received_message.data.decode("utf-8") == data.model_dump_json()
    assert received_message.attributes.get("a") == "b"
