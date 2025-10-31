# GcpSubscription

## Constructor

* `subscription_id` - Pub/Sub subscription ID, e.g. `unit-tests-sub`.
* `project_id` - GCP project ID, if not provided, it will use the one from environment variable `GOOGLE_PROJECT` or `GOOGLE_CLOUD_PROJECT`.
* `clazz` - Optional Pydantic model class to convert received messages to. If not provided, raw messages will be returned with `data` and `attributes` fields.
* `processing_timeout` - How long the subscription will wait for messages before timing out. Default is `5.0` seconds.
* `per_message_timeout` - How long it will wait for each message before timing out. Default is `1.0` seconds.

## Methods

* `create(self, exist_ok: bool = False) -> Self` - Creates the subscription in GCP if it does not exist. If `exist_ok` is set to `True`, it will not raise an error if the subscription already exists.
* `delete(self) -> None` - Deletes the subscription in GCP.
* `receive_messages(self) -> Generator[Message, None, None]` - Returns a generator that yields messages from the subscription.
* `__iter__(self) -> Generator[T, None, None]` - Allows the subscription to be used as an iterable. It will yield messages converted to Pydantic objects of type `clazz` if provided. Otherwise, it will raise `TypeError` if `clazz` is not set.
* `receive_firsreceive_first_message(self, filter: Callable[[Message], bool]) -> Optional[Message]` - Receives the first message that matches the filter function. The filter function should take a `Message` object and return `True` if the message matches the criteria. It is useful for testing.
* `run_push_emulator(self, client: TestClient, endpoint: str) -> GcpPubsubPushEmulator` - Runs a push emulator that listens for messages from the subscription and forwards them to the specified FastAPI endpoint using the provided `TestClient`. It returns a `GcpPubsubPushEmulator` object that can be used to check the status of the emulator and retrieve received messages and responses.
* `exists(self) -> bool` - Checks if the subscription exists in GCP.
* `clear(self)` -> None - Clears all pending messages in the subscription.
* `wait_until_empty(self, timeout: float = 5.0, check_interval: float = 1.0) -> None` - Waits until the subscription is empty or the timeout is reached. It checks the subscription every `check_interval` seconds. Useful for testing.

## Usage

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
