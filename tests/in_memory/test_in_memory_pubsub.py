import logging
import time
from collections.abc import Generator

import pytest
from fastapi import FastAPI, Request
from pydantic import BaseModel

from ampf.base.base_subscription import BaseSubscription
from ampf.base.base_topic import BaseTopic
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse
from ampf.in_memory.in_memory_factory import InMemoryFactory
from ampf.testing.api_test_client import ApiTestClient

topic_id = "xxx"

_log = logging.getLogger(__name__)


@pytest.fixture
def factory():
    return InMemoryFactory()


class D(BaseModel):
    name: str = "D"


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
    received_message = subscription.receive_message(timeout=0.5)
    # Then: The received message is None
    assert received_message is None


def test_publish_and_receive(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # And: A topic and subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription()
    # When: A message is published via topic
    message_id = topic.publish(D(name="Hello, World!"), attrs={"key": "value"})
    # Then: The message can be received via subscription
    received_message = subscription.receive_message(timeout=0.5)
    assert received_message is not None
    assert received_message.messageId == message_id
    assert received_message.decoded_data(D).name == "Hello, World!"
    assert received_message.attributes
    assert received_message.attributes["key"] == "value"


def test_publish_and_receive_messages(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # And: A topic and subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription()
    # And: Messages are published via topic
    d1 = D(name="Hello, World 1!")
    d2 = D(name="Hello, World 2!")
    message1_id = topic.publish(d1)
    message2_id = topic.publish(d2)
    # When: Messages can be received via subscription
    for received_message in subscription.receive_messages(processing_timeout=0.5, per_message_timeout=0.1):
        # Then: The received message is one of the published messages
        assert received_message is not None
        assert received_message.messageId in [message1_id, message2_id]
        assert received_message.decoded_data(D) in [d1, d2]


def test_publish_and_iterate_payloads(factory: InMemoryFactory):
    # Given: A factory
    assert factory
    # And: A topic and subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription(clazz=D, processing_timeout=0.5)
    # And: A messages are published via topic
    topic.publish(D(name="Hello, World 1!"))
    topic.publish(D(name="Hello, World 2!"))
    # When: Messages can be received via subscription
    for payload in subscription:
        # Then: The received message is one of the published messages
        assert payload.name in ["Hello, World 1!", "Hello, World 2!"]


@pytest.fixture
def client() -> Generator[ApiTestClient]:
    app = FastAPI()

    @app.post("/pub-sub")
    async def handle_post(request: Request, pubsub_req: GcpPubsubRequest) -> GcpPubsubResponse:
        app: FastAPI = request.app
        app.state.last_message = pubsub_req.decoded_data(D)
        _log.warning(app.state.last_message)
        return GcpPubsubResponse(status="acknowledged", messageId=pubsub_req.message.messageId)

    @app.get("/last-message")
    async def handle_get(request: Request) -> D:
        app: FastAPI = request.app
        _log.warning(app.state.__dict__)
        return app.state.last_message

    yield ApiTestClient(app)


def test_push_emulator(factory: InMemoryFactory, client: ApiTestClient):
    # Given: A topic and subscription
    topic = factory.create_topic(topic_id)
    subscription = topic.create_subscription()
    # And: A push emulator
    with subscription.run_push_emulator(client, "/pub-sub/") as sub_emulator:
        # When: A message is published via topic
        topic.publish(D(name="X"))
        while not sub_emulator.is_finished(timeout=1):
            time.sleep(0.1)
    # Then: The message was sent via http to application
    m = client.get_typed("/last-message", 200, D)
    assert m.name == "X"
