import time

from pydantic import BaseModel

from ampf.gcp import GcpSubscription, GcpTopic


class D(BaseModel):
    name: str


def test_basic_pubsub(topic: GcpTopic, subscription: GcpSubscription):
    # Given: A topic and a typed subscription
    typed_subscription = GcpSubscription(subscription.subscription_id, subscription.project_id, D)
    # When: Message is published
    data = D(name=f"Test message {time.time()}")
    topic.publish(data)
    # Then: Message is received
    received_data = typed_subscription.receive_first_payload(lambda msg_data: msg_data == data)
    assert received_data


def test_pubsub_with_attrs(topic: GcpTopic, subscription: GcpSubscription):
    # Given: A topic and a subscription
    # When: Message is published with attrs
    data = D(name=f"Test message {time.time()}")
    topic.publish(data, {"a": "b"})
    # Then: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["a"] == "b")
    assert received_message
    assert received_message.data.decode("utf-8") == data.model_dump_json()
    assert received_message.attributes.get("a") == "b"


def test_pubsub_with_response_topic(topic: GcpTopic, subscription: GcpSubscription):
    # Given: A topic and a subscription
    # When: Message is published with attrs
    data = D(name=f"Test message {time.time()}")
    topic.publish(data, response_topic="xxx")
    # Then: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["response_topic"] == "xxx")
    assert received_message
    assert received_message.data.decode("utf-8") == data.model_dump_json()
    assert received_message.attributes.get("response_topic") == "xxx"
