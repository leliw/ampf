# GcpTopic

Sends message to Pub/Sub topic.

## Constructor

* `topic_id` - Pub/Sub topic ID, e.g. `unit-tests`.
* `project_id` - GCP project ID, if not provided, it will use the one from environment variable `GOOGLE_PROJECT` or `GOOGLE_CLOUD_PROJECT`.

## Methods

* `create(self, exist_ok: bool = False) -> Self` - Creates the topic in GCP if it does not exist. If `exist_ok` is set to `True`, it will not raise an error if the topic already exists.
* `delete(self) -> None` - Deletes the topic in GCP.
* `create_subscription(self, subscription_id: str, clazz: Optional[Type[T]] = None, processing_timeout: float = 5.0, per_message_timeout: float = 1.0, exist_ok: bool = False) -> GcpSubscription[T]` - Creates a subscription in GCP for the topic. The `subscription_id` is the ID of the subscription to create. If `clazz` is provided, it will be used to convert received messages to Pydantic objects of type `clazz`. The `processing_timeout` and `per_message_timeout` parameters control how long the subscription will wait for messages and how long it will wait for each message, respectively. If `exist_ok` is set to `True`, it will not raise an error if the subscription already exists.
* `publish(self, data: T | str | bytes, attrs: Optional[Dict[str, str]] = None, response_topic: Optional[str] = None, sender_id: Optional[str] = None) -> str:` - Publishes data to the topic. The data can be any Pydantic model or a simple object that can be serialized to JSON. If `attributes` are provided, they will be sent as additional metadata.
* `publish_async(self, data: T | str | bytes, attrs: Optional[Dict[str, str]] = None, response_topic: Optional[str] = None, sender_id: Optional[str] = None) -> str:` - Asynchronous version of `publish()`.
* `exists(self) -> bool` - Checks if the topic exists in GCP.

## Usage

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
