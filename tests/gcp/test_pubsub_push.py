import logging
from uuid import uuid4

import pytest
from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from ampf.gcp import GcpSubscription, GcpTopic
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse


class D(BaseModel):
    name: str


@pytest.fixture
def app():
    _log = logging.getLogger(__name__)
    app = FastAPI()
    router = APIRouter()

    @router.post("")
    async def handle_push(request: GcpPubsubRequest) -> GcpPubsubResponse:
        try:
            payload = request.decoded_data(D)
            payload.name = f"Processed: {payload.name}"
            request.publish_response(payload)

            # Return acknowledgment
            return GcpPubsubResponse(status="acknowledged", messageId=request.message.messageId)

        except ValidationError as e:
            _log.error("Error processing message ID: %s: %s", request.message.messageId, e)
            raise HTTPException(status_code=400, detail=f"Wrong message format: {e}")
        except Exception as e:
            _log.error("Error processing message ID %s: %s", request.message.messageId, e)
            raise HTTPException(status_code=500, detail=f"Error processing message: {e}")

    app.include_router(router, prefix="/pub-sub")
    return app


@pytest.fixture
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
