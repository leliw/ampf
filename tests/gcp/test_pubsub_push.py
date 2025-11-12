import logging
import time
import uuid
from typing import Annotated, AsyncIterator, Iterator, List
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ampf.gcp import GcpSubscription, GcpTopic, gcp_pubsub_process_push, gcp_pubsub_push_handler
from ampf.gcp.gcp_async_factory import GcpAsyncFactory
from ampf.gcp.gcp_factory import GcpFactory
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse
from ampf.gcp.subscription_processor import SubscriptionProcessor


class D(BaseModel):
    name: str


@pytest.fixture(scope="module")
def topic2():
    topic_id = "ampf_unit_tests_step2_" + uuid.uuid4().hex[:6]
    topic = GcpTopic(topic_id).create(exist_ok=True)
    yield topic
    topic.delete()


@pytest.fixture(scope="module")
def subscription2(topic2: GcpTopic):
    subscription = topic2.create_subscription(exist_ok=True)
    yield subscription
    subscription.delete()


@pytest.fixture(scope="module")
def subscription(topic: GcpTopic):
    subscription = topic.create_subscription(clazz=D, processing_timeout=10.0, exist_ok=True)
    yield subscription
    subscription.delete()


def get_config() -> dict:
    return {"msg": "Processed:"}


ConfigDep = Annotated[dict, Depends(get_config)]


def get_factory() -> GcpFactory:
    return GcpFactory()


FactoryDep = Annotated[GcpFactory, Depends(get_factory)]


def get_async_factory() -> GcpAsyncFactory:
    return GcpAsyncFactory()


AsyncFactoryDep = Annotated[GcpAsyncFactory, Depends(get_async_factory)]


@pytest.fixture(scope="module")
def app(topic: GcpTopic, topic2: GcpTopic):
    _log = logging.getLogger(__name__)
    app = FastAPI()
    router = APIRouter()

    @router.post("/one_param")
    @gcp_pubsub_push_handler()
    async def handle_push_d1(payload: D, f: FactoryDep) -> D:
        payload.name = f"Processed: {payload.name}"
        return payload

    @router.post("/payload_first")
    @gcp_pubsub_push_handler(factory_dep=FactoryDep)
    async def handle_push_d2(payload: D, p: ConfigDep) -> D:
        payload.name = f"{p['msg']} {payload.name}"
        return payload

    @router.post("/payload_last")
    @gcp_pubsub_push_handler()
    async def handle_push_d3(p: ConfigDep, payload: D) -> D:
        payload.name = f"{p['msg']} {payload.name}"
        return payload

    @router.post("/def-resp-topic")
    @gcp_pubsub_push_handler()
    async def handle_push_d4(p: ConfigDep, payload: D, request: GcpPubsubRequest) -> D:
        request.set_default_response_topic(topic.topic_id)
        payload.name = f"{p['msg']} {payload.name}"
        return payload

    @router.post("/async_value")
    @gcp_pubsub_push_handler()
    async def handle_push_async_value(payload: D) -> D:
        payload.name = f"Processed: {payload.name}"
        return payload

    @router.post("/sync_value")
    @gcp_pubsub_push_handler()
    def handle_push_sync_value(payload: D) -> D:
        payload.name = f"Processed: {payload.name}"
        return payload

    @router.post("/sync_iterator")
    @gcp_pubsub_push_handler()
    def handle_push_sync_iterator(payload: D) -> Iterator[D]:
        payload.name = f"Processed: {payload.name}"
        yield payload

    @router.post("/async_iterator")
    @gcp_pubsub_push_handler()
    async def handle_push_async_iterator(payload: D) -> AsyncIterator[D]:
        payload.name = f"Processed: {payload.name}"
        yield payload

    @router.post("/multi_return")
    @gcp_pubsub_push_handler()
    async def handle_push_multi_return(payload: D) -> AsyncIterator[D]:
        for i in range(3):
            yield D(name=f"Processed: {payload.name} {i}")

    @router.post("/step-1")
    @gcp_pubsub_push_handler()
    async def handle_push_step_1(request: GcpPubsubRequest, payload: D) -> D:
        request.forward_response_to_topic(topic2.topic_id)
        return D(name=f"Step 1 processed: {payload.name}")

    @router.post("/step-2")
    @gcp_pubsub_push_handler()
    async def handle_push_step_2(payload: D) -> D:
        return D(name=f"Step 2 processed: {payload.name}")

    @router.post("/list")
    @gcp_pubsub_push_handler()
    async def handle_push_list(payload: D) -> List[D]:
        return [payload, payload]

    @router.post("/value-exception")
    @gcp_pubsub_push_handler()
    async def handle_value_exception(payload: D, f: FactoryDep) -> D:
        raise ValueError("Value exception", payload)

    class DProcessor(SubscriptionProcessor[D]):
        async def process_payload(self, payload: D) -> D:
            self.called = True
            return D(name=f"Processed by processor: {payload.name}")

    def get_d_processor(async_factory: AsyncFactoryDep) -> DProcessor:
        return DProcessor(async_factory, D)

    DProcessorDep = Annotated[DProcessor, Depends(get_d_processor)]

    @router.post("/processor")
    async def handle_processor(processor: DProcessorDep, request: GcpPubsubRequest) -> GcpPubsubResponse: # type: ignore
        return await gcp_pubsub_process_push(processor, request)

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


def test_pubsub_push_default_response_topic(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes without response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/def-resp-topic", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed: {d.name}"


@pytest.fixture(params=["sync_value", "async_value", "sync_iterator", "async_iterator"])
def endpoint(request):
    return f"/pub-sub/{request.param}"


def test_different_function_types(topic: GcpTopic, subscription: GcpSubscription, client: TestClient, endpoint: str):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post(endpoint, json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed: {d.name}"


def test_multi_return(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/multi_return", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Messages are received
    cnt = 0
    for message in subscription.receive_messages():
        if message.attributes["sender_id"] == sender_id:
            cnt += 1
            assert D.model_validate_json(message.data.decode("utf-8")).name.startswith(f"Processed: {d.name}")
        if cnt == 3:
            break


def test_multistep(topic: GcpTopic, subscription: GcpSubscription, subscription2: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)

    with subscription2.run_push_emulator(client, "/pub-sub/step-2") as sub_emulator:
        # When: The request is posted
        response = client.post("/pub-sub/step-1", json=req.model_dump())
        # Then: Response is OK
        assert response.status_code == status.HTTP_200_OK
        while not sub_emulator.isfinished(timeout=20, expected_responses=1):
            time.sleep(0.1)
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    assert received_message.attributes["sender_id"] == sender_id
    # And: Message is processed
    assert (
        D.model_validate_json(received_message.data.decode("utf-8")).name
        == f"Step 2 processed: Step 1 processed: {d.name}"
    )


def test_pubsub_push_returns_list(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/list", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    i = 0
    for message in subscription.receive_messages():
        if message.attributes["sender_id"] == sender_id:
            i += 1
        # And: Message is processed
        assert D.model_validate_json(message.data.decode("utf-8")).name == d.name
        if i == 2:
            break
    assert i == 2


class D2(BaseModel):
    wrong_field: str = "wrong"


def test_pubsub_push_validation_exception(topic: GcpTopic, client: TestClient):
    # Given: Message payload
    d = D2()
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, response_topic=topic.topic_id, sender_id=uuid4().hex)
    # When: The request is posted
    response = client.post("/pub-sub/one_param", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Wrong message format" in response.text


def test_pubsub_push_value_exception(topic: GcpTopic, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, response_topic=topic.topic_id)
    # When: The request is posted
    response = client.post("/pub-sub/value-exception", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Value exception" in response.text


def test_pubsub_push_processor(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: Message payload
    d = D(name="test")
    # And: Message attributes with response_topic and sender_id
    sender_id = uuid4().hex
    attributes = {"response_topic": topic.topic_id, "sender_id": sender_id}
    # And: A fake request pushed from a subscription
    req = GcpPubsubRequest.create(d, attributes=attributes)
    # When: The request is posted
    response = client.post("/pub-sub/processor", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed by processor: {d.name}"