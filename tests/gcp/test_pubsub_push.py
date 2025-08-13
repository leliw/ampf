import json
import logging
from uuid import uuid4

import pytest
from fastapi import APIRouter, FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ampf.gcp import GcpSubscription, GcpTopic, gcp_pubsub_push_handler
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest


class D(BaseModel):
    name: str


@pytest.fixture
def app():
    _log = logging.getLogger(__name__)
    app = FastAPI()
    router = APIRouter()

    @router.post("")
    @gcp_pubsub_push_handler()
    async def handle_push_d(payload: D) -> D:
        payload.name = f"Processed: {payload.name}"
        return payload

    app.include_router(router, prefix="/pub-sub")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_pubsub_push_with_attrs(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    result = client.get("/openapi.json")
    assert result.status_code == 200
    r = result.json()
    print(json.dumps(r, indent=2))
    assert "/pub-sub" in r["paths"]

    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub", json=req.model_dump())
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
    response = client.post("/pub-sub", json=req.model_dump())

    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
