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
Topics and subscriptions have to be created in advance.

```bash
gcloud pubsub topics create unit-tests
gcloud pubsub subscriptions create unit-tests-sub --topic unit-tests
```

### GcpTopic

Sends message to Pub/Sub topic.

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
