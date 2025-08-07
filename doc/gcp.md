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

An example of an endpoint receiving messages.

```python
router = APIRouter(tags=["Pub/Sub Push"])


class PubsubMessage(BaseModel):
    messageId: Optional[str] = None
    attributes: Optional[Dict[str, str]] = None
    data: str
    publishTime: Optional[str] = None


class PushRequest(BaseModel):
    message: PubsubMessage
    subscription: str


@router.post("")
async def handle_push(request: PushRequest):
    try:
        decoded_data = base64.b64decode(request.message.data).decode("utf-8")
        response_topic_name = request.message.attributes.get('response_topic')

        # Convert data to desired body
        body = ChunksRequest.model_validate_json(decoded_data)
        response = ... # Do something with body
        # Send response to publisher
        GcpTopic(response_topic_name).publish(response.model_dump_json())
            
        return {"status": "acknowledged", "messageId": request.message.messageId}
    except ValidationError as e:
        _log.error("Error processing message ID: %s: %s", request.message.messageId, e)
        raise HTTPException(status_code=400, detail=f"Wrong message format: {e}")

    except Exception as e:
        _log.error("Error processing message ID: %s: %s", request.message.messageId, e)
        raise HTTPException(status_code=500, detail=f"Error processing message: {e}")
```
