# gcp_pubsub_push_handler()

This is a decorator for handling GCP Pub/Sub push messages. It can be used to wrap FastAPI endpoints that receive push messages from Pub/Sub.
Below code is coresponding to the above endpoint, but using the decorator.

## Parameters

* factory_dep: Optional[Type[T] | Any] = None - A dependency that will be used to create `GcpTopic` instances. It allows to use different factories for different project_ids.
  When is not provided, a `GcpTopic` will be created with default parameters.

```python
def get_factory() -> GcpFactory:
    return GcpFactory()

FactoryDep = Annotated[GcpFactory, Depends(get_factory)]

@router.post("/payload_first")
@gcp_pubsub_push_handler(factory_dep=FactoryDep)
async def handle_push_d2(payload: D, p: ConfigDep) -> D:
    payload.name = f"{p['msg']} {payload.name}"
    return payload
```

If a factory is provided as a parameter, it also will be used to create `GcpTopic` instance.

```python
@router.post("/one_param")
@gcp_pubsub_push_handler()
async def handle_push_d1(payload: D, f: FactoryDep) -> D:
    payload.name = f"Processed: {payload.name}"
    return payload
```

## Basic usage

```python
@router.post("")
@gcp_pubsub_push_handler()
async def handle_push(payload: D) -> D:
    payload.name = f"Processed: {payload.name}"
    return payload
```

If decorated function returns a Pydantic model, it will be automatically converted to `GcpPubsubResponse` and sent back as a response by the method `publish_response()`.
The message is acknowledged if the function does not raise an exception.

## Setting response topic

You can also add dependencies as parameter and set `default_response_topic` (it is used **only if** there are not `response_topic` message attribute).

```python
@router.post("/markdown-converted")
@gcp_pubsub_push_handler()
async def handle_push_markdown_converted(
    config: ConfigDep, orchestrator: JobOrchestratorDep, request: GcpPubsubRequest, payload: PdfConversionResponse
) -> ChunksRequest:
    request.set_default_response_topic(config.chunking_requests_topic)
    return orchestrator.handle_markdown_converted(payload)
```

There is also `set_response_topic()` method to set the response topic dynamically. It **overrides** both `default_response_topic` and `response_topic` attribute.

## Handling iterators

The wrapped function can also return an (async) generator to send multiple messages as response.

```python
@router.post("/multi_return")
@gcp_pubsub_push_handler()
async def handle_push_multi_return(payload: D) -> AsyncIterator[D]:
    for i in range(3):
        yield D(name=f"Processed: {payload.name} {i}")
```

## Multiple steps processing

You can also chain multiple steps of processing using Pub/Sub topics. The first step processes the message and forwards the response to another topic, where another subscription can receive it and process it further. Just use `request.forward_response_to_topic(next_step_topic)` method to set the next topic.
`forward_response_to_topic()` takes precedence over `default_response_topic` and `response_topic` attribute, but `response_topic` is passed to the next step as an attribute, so next step can return the response to the original sender or forward it to next step.

```python
    @router.post("/step-1")
    @gcp_pubsub_push_handler()
    async def handle_push_step_1(request: GcpPubsubRequest, payload: D) -> D:
        request.forward_response_to_topic(topic2.topic_id)
        return D(name=f"Step 1 processed: {payload.name}")

    @router.post("/step-2")
    @gcp_pubsub_push_handler()
    async def handle_push_step_2(payload: D) -> D:
        return D(name=f"Step 2 processed: {payload.name}")
```

## Testing

### Preparation

To test GCP Pub/Sub functionality, you can use fixtures to create a topic and a subscription. The topic will be used to publish messages, and the subscription will be used to receive them.

```python
import uuid

import pytest

from ampf.gcp.gcp_topic import GcpTopic


@pytest.fixture(scope="session")
def topic():
    topic_id = "ampf_unit_tests_" + uuid.uuid4().hex[:6]
    topic = GcpTopic(topic_id).create(exist_ok=True)
    yield topic
    topic.delete()


@pytest.fixture(scope="session")
def subscription(topic: GcpTopic):
    subscription_id = f"{topic.topic_id}_sub"
    subscription = topic.create_subscription(subscription_id, exist_ok=True)
    yield subscription
    subscription.delete()
```

### Testing sending messages

To test code that sends messages to a Pub/Sub topic, you can use the below example. Replace `topic.publish(data)` with your actual code that sends messages.

```python
def test_pubsub(topic: GcpTopic, subscription: GcpSubscription):
    # Given: Message payload
    data = D(name=f"Test message {time.time()}")
    # When: Message is published
    topic.publish(data)
    # Then: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.data.decode("utf-8") == data.model_dump_json())
    assert received_message
```

### Testing receiving messages (Push)

To test code that receives messages from a Pub/Sub subscription, you can use the below example. Replace `GcpPubsubRequest` with your actual request structure and
the endpoint with your actual FastAPI endpoint. At the end, you can check if the message was processed correctly.

```python
def test_pubsub_push_with_attrs(topic: GcpTopic, subscription: GcpSubscription, client: TestClient):
    # Given: A fake request pushed from a subscription
    sender_id = uuid4().hex
    req = GcpPubsubRequest.create(D(name="test"), attributes={"response_topic": topic.topic_id, "sender_id": sender_id})
    # When: The request is posted
    response = client.post("/pub-sub", json=req.model_dump())
    # Then: Response is OK
    assert response.status_code == status.HTTP_200_OK
    # And: Message is received
    received_message = subscription.receive_first_message(lambda msg: msg.attributes["sender_id"] == sender_id)
    assert received_message
    # And: Message is processed
    assert D.model_validate_json(received_message.data.decode("utf-8")).name == f"Processed: {d.name}"
```

### Testing Pub/Sub push subscription workaround

To test the complete flow of sending a message to a topic, receiving it in a push subscription, you can use the following example.
There is a workaround to handle the push subscription by posting the received message to a FastAPI endpoint.

```python
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
```

You can also use the `run_push_emulator` method to do the same thing in a more elegant way.

```python
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
```
