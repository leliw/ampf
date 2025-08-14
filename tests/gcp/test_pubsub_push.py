import logging
import time
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ampf.gcp import GcpSubscription, GcpTopic, gcp_pubsub_push_handler
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest


class D(BaseModel):
    name: str

@pytest.fixture(scope="module")
def subscription(topic: GcpTopic):
    subscription = topic.create_subscription(clazz=D, processing_timeout=10.0,exist_ok=True)
    yield subscription
    subscription.delete()

def get_config() -> dict:
    return {"msg": "Processed:"}


ConfigDep = Annotated[dict, Depends(get_config)]


@pytest.fixture(scope="module")
def app():
    _log = logging.getLogger(__name__)
    app = FastAPI()
    router = APIRouter()

    @router.post("/one_param")
    @gcp_pubsub_push_handler()
    async def handle_push_d1(payload: D) -> D:
        payload.name = f"Processed: {payload.name}"
        return payload

    @router.post("/payload_first")
    @gcp_pubsub_push_handler()
    async def handle_push_d2(payload: D, p: ConfigDep) -> D:
        payload.name = f"{p['msg']} {payload.name}"
        return payload

    @router.post("/payload_last")
    @gcp_pubsub_push_handler()
    async def handle_push_d3(p: ConfigDep, payload: D) -> D:
        payload.name = f"{p['msg']} {payload.name}"
        return payload

    app.include_router(router, prefix="/pub-sub")
    return app


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)


def test_pubsub_push_with_attrs(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/one_param", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed: {d.name}"


def test_pubsub_push_subscription_workaround(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Example code to test flow topic -> subscription -> push -> post
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with  sender_id
    sender_id = uuid4().hex
    attributes = {"sender_id": sender_id}
    topic.publish(d, attributes)

    # When: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: The received message is converted to GcpPubsubRequest
    req = GcpPubsubRequest.create_from_message(received_message, subscription.subscription_id)
    # And: The request is posted
    response = client.post("/pub-sub/one_param", json=req.model_dump())

    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK


def test_pubsub_push_emulator(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with  sender_id
    sender_id = uuid4().hex
    attributes = {"sender_id": sender_id}
    # When: emulator is run
    with subscription.run_push_emulator(client, "/pub-sub/one_param") as sub_emulator:
        # And: Message is published
        topic.publish(d, attributes)
        while not sub_emulator.isfinished(timeout=5, expected_responses=1):
            time.sleep(0.1)
        # Then: The sent message is received
        assert sub_emulator.messages[0].attributes["sender_id"] == sender_id
        # And: The message payload is decoded
        assert sub_emulator.payloads[0].name == d.name
        # And: The endpoint response is OK
        assert sub_emulator.responses[0].status_code == status.HTTP_200_OK




def test_pubsub_push_payload_first(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/payload_first", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed: {d.name}"


def test_pubsub_push_payload_last(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/payload_last", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed: {d.name}"
