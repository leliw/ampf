# GCP

GCP package implements abstract classes using Google Cloud Platform.

## Configuration

All configuration parameters are defined in `ServerConfig` class and can be set
using environment variables.

```python
class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    version: str = "0.0.1"
    data_dir: str = "./data/"

    gcp_root_storage: Optional[str] = None
```

Environment variables for GCP configuration:

* GCP_ROOT_STORAGE - Root storage name e.g. `projects/ampf`

## GcpFactory

### Constructor

You can pass `root_storage` parameter to the constructor to set the root storage.
This is the way to use separate storage for each project in one GCP project.

## GcpStorage

### Vector search - embedding

If you want to use embeddings and vector search, there is a special solution.
Create field named `embedding` of type `List[float]` and add special index in
firestore database. Then you can use `find_nearest()` method which uses vector
serach over `embedding` field.

Creating index:

```bash
gcloud firestore indexes composite create \
    --project=development-428212 \
    --collection-group=tests-ampf-gcp \
    --query-scope=COLLECTION \
    --field-config=vector-config='{"dimension":"3","flat": "{}"}',field-path=embedding
```

Code sample:

```python
class TC(BaseModel):
    name: str
    embedding: List[float] = None

# Given: Data with embedding
tc1 = TC(name="test1", embedding=[1.0, 2.0, 3.0])
tc2 = TC(name="test2", embedding=[4.0, 5.0, 6.0])
# When: Save them
storage.put("1", tc1)
storage.put("2", tc2)
# And: Find nearest
nearest = list(storage.find_nearest(tc1.embedding))
# Then: All two are returned
assert len(nearest) == 2
# And: The nearest is the first one
assert nearest[0] == tc1
# And: The second is the second
assert nearest[1] == tc2
```

## GcpBlobStorage

Stores blobs in GCP using **Cloud Storage** service.
The constructor has an extra parameter `bucket_name` which appoints
used bucket. If all storages use the same bucket, you can set default
bucket with `init_client()` class method.

```python
GcpBlobStorage.init_client(
    bucket_name=server_config.google_bucket_name
)
```

## Pub/Sub

Helper classes for Pub/Sub.

### GcpTopic

Sends message to Pub/Sub topic.

#### Constructor

* `topic_id` - Pub/Sub topic ID, e.g. `unit-tests`.
* `project_id` - GCP project ID, if not provided, it will use the one from environment variable `GOOGLE_PROJECT` or `GOOGLE_CLOUD_PROJECT`.

#### Methods

* `create(self, exist_ok: bool = False) -> Self` - Creates the topic in GCP if it does not exist. If `exist_ok` is set to `True`, it will not raise an error if the topic already exists.
* `delete(self) -> None` - Deletes the topic in GCP.
* `create_subscription(self, subscription_id: str, clazz: Optional[Type[T]] = None, processing_timeout: float = 5.0, per_message_timeout: float = 1.0, exist_ok: bool = False) -> GcpSubscription[T]` - Creates a subscription in GCP for the topic. The `subscription_id` is the ID of the subscription to create. If `clazz` is provided, it will be used to convert received messages to Pydantic objects of type `clazz`. The `processing_timeout` and `per_message_timeout` parameters control how long the subscription will wait for messages and how long it will wait for each message, respectively. If `exist_ok` is set to `True`, it will not raise an error if the subscription already exists.
* `publish(data: T, attributes: Optional[Dict[str, str]] = None) -> None` - Publishes data to the topic. The data can be any Pydantic model or a simple object that can be serialized to JSON. If `attributes` are provided, they will be sent as additional metadata.

#### Usage

```python
topic = GcpTopic(project_id, topic_id)
data = D(name=f"Test message {time.time()}")
topic.publish(data)
```

You can also pass attributes to the message. They will be sent as
additional metadata.

```python
topic = GcpTopic(project_id, topic_id)
data = D(name=f"Test message {time.time()}")
attributes = {"key1": "value1", "key2": "value2"}
topic.publish(data, attributes)
```

### GcpSubscription

#### Constructor

* `subscription_id` - Pub/Sub subscription ID, e.g. `unit-tests-sub`.
* `project_id` - GCP project ID, if not provided, it will use the one from environment variable `GOOGLE_PROJECT` or `GOOGLE_CLOUD_PROJECT`.
* `clazz` - Optional Pydantic model class to convert received messages to. If not provided, raw messages will be returned with `data` and `attributes` fields.
* `processing_timeout` - How long the subscription will wait for messages before timing out. Default is `5.0` seconds.
* `per_message_timeout` - How long it will wait for each message before timing out. Default is `1.0` seconds.

#### Methods

* `create(self, exist_ok: bool = False) -> Self` - Creates the subscription in GCP if it does not exist. If `exist_ok` is set to `True`, it will not raise an error if the subscription already exists.
* `delete(self) -> None` - Deletes the subscription in GCP.
* `receive_messages(self) -> Generator[Message, None, None]` - Returns a generator that yields messages from the subscription.
* `__iter__(self) -> Generator[T, None, None]` - Allows the subscription to be used as an iterable. It will yield messages converted to Pydantic objects of type `clazz` if provided. Otherwise, it will raise `TypeError` if `clazz` is not set.
* `receive_firsreceive_first_message(self, filter: Callable[[Message], bool]) -> Optional[Message]` - Receives the first message that matches the filter function. The filter function should take a `Message` object and return `True` if the message matches the criteria. It is useful for testing.

#### Usage

Receives messages from Pub/Sub topic and return them as a generator.

```python
subscription = GcpSubscription(project_id, subscription_id, D)
for data in subscription:
    print(data)
```

If you pass class `D` to the constructor, it will automatically convert
the received messages to Pydantic objects of type `D`. Otherwise, it will return
raw message with `data` and `attributes` fields.

```python
subscription = GcpSubscription(project_id, subscription_id)
for message in subscription:
    print(message.data.decode("utf-8")
    print(message.attributes)
```

Code sample:

```python
topic = GcpTopic(topic_id, project_id)
# And: Subscription is created
subscription = GcpSubscription(subscription_id, project_id, D, processing_timeout=5.0, per_message_timeout=1.0)
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
```

### Receive push notification

For services launched in GCP, delivering messages using a standard subscription (Pull) message is not recommended.
A better solution is to deliver (Push) - sending a message to a specified endpoint.

There are special classes to handle this:

* `GcpPubsubRequest`
* `GcpPubsubMessage`
* `GcpPubsubResponse`

An example of an endpoint receiving messages.

```python
router = APIRouter(tags=["Pub/Sub Push"])

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
```

### gcp_pubsub_push_handler

This is a decorator for handling GCP Pub/Sub push messages. It can be used to wrap FastAPI endpoints that receive push messages from Pub/Sub.
Below code is coresponding to the above endpoint, but using the decorator.

```python
@router.post("")
@gcp_pubsub_push_handler()
async def handle_push(payload: D) -> D:
    payload.name = f"Processed: {payload.name}"
    return payload
```

If decorated function returns a Pydantic model, it will be automatically converted to `GcpPubsubResponse` and sent back as a response by the method `publish_response()`.
The message is acknowledged if the function does not raise an exception.

You can also add dependencies as parameter and set `default_response_topic` (it is used if there are not `response_topic` message attribute).

```python
@router.post("/markdown-converted")
@gcp_pubsub_push_handler()
async def handle_push_markdown_converted(
    config: ConfigDep, orchestrator: JobOrchestratorDep, request: GcpPubsubRequest, payload: PdfConversionResponse
) -> ChunksRequest:
    request.set_default_response_topic(config.chunking_requests_topic)
    return orchestrator.handle_markdown_converted(payload)
```

#### Handling iterators

The wrapped function can also return an (async) generator to send multiple messages as response.

```python
@router.post("/multi_return")
@gcp_pubsub_push_handler()
async def handle_push_multi_return(payload: D) -> AsyncIterator[D]:
    for i in range(3):
        yield D(name=f"Processed: {payload.name} {i}")
```

#### Multiple steps processing

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

### Testing

#### Preparation

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

#### Testing sending messages

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

#### Testing receiving messages (Push)

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

#### Testing Pub/Sub push subscription workaround

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
