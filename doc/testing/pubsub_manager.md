# PubSubManager

A utility for managing Google Cloud Pub/Sub topics and subscriptions during testing. It provides methods to create and delete topics and subscriptions, publish messages, and pull messages for verification.

There is also a fixture `pubsub_manager` for easy integration into test cases. It deletes all created topics and subscriptions after the test completes to ensure a clean state.

## Methods

- `prepare_topic[T: BaseModel](self, topic_id: str, clazz: Optional[Type[T]] = None) -> GcpTopic[T]` - Creates new or gets existing a Pub/Sub topic with the given name.
- `prepare_subscription[T: BaseModel](self, subcription_id: str, clazz: Optional[Type[T]] = None, topic_id: Optional[str] = None) -> GcpSubscription[T]` - Creates new or gets existing a Pub/Sub subscription for the specified topic.
- `prepare_resources(self, config: BaseModel) -> None` - Prepares topics and subscriptions based on the provided configuration model.
- `publish(self, topic_id: str, data: BaseModel) -> None` - Publishes a message to the specified topic.
- `wait_until_empty(self, subscription_id: str, timeout: float = 10.0) -> None` - Waits until the specified subscription has no messages left to process or until the timeout is reached.
- `cleanup(self) -> None` - Deletes all topics and subscriptions created during the test.

## Usage

### Preparing topics and subscriptions

Creating topics and subscriptions is slow, so it's best to prepare them once per test.

```python
@pytest.fixture(scope="session")
def prefix() -> str:
    return "unit_tests_" + uuid4().hex[:6]


@pytest.fixture(scope="session")
def session_config(prefix: str, pubsub_manager: PubSubManager) -> ServerConfig:
    config = ServerConfig(
        git_commit_requests_topic=f"{prefix}-git-commit-requests",
        git_commit_requests_subscription=f"{prefix}-git-commit-requests-sub",
    )
    pubsub_manager.prepare_resources(config)
    return config


@pytest.fixture
def config(tmp_path: Path, session_config: ServerConfig) -> ServerConfig:
    config = session_config.model_copy()
    config.data_dir = str(tmp_path)
    config.gcp_bucket_name = None
    config.gcp_root_storage = None
    return config
```

### Publishing a message and waiting for processing

```python
# When: A message is published
pubsub_manager.publish(config.git_commit_requests_topic, req)
# And: The application processes messages
await pubsub_manager.wait_until_empty(config.git_commit_requests_subscription)
```
