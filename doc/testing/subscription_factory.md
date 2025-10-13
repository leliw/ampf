# subscription_factory

Helper for creating GCP Pub/Sub (topics and) subscriptions. If a subscription (topic) is cerated, then is deleted after test.

## Parameters

* `topic_name`: str - The name of the topic.
* `clazz`: Type[T] - The Pydantic model class for the subscription's messages.
* `subcription_name`: Optional[str] = None - The name of the subscription. If not provided, a unique name will be generated.

## Usage

Declare fixture in `conftest.py`

```python
from ampf.testing import *  # noqa: F403
```

Then import only `SubscriptionFactory` class.

```python
@pytest.fixture
def config() -> ServerConfig:
    config = ServerConfig()
    config.response_topic_name = "my-response-topic2-" + uuid4().hex
    return config


@pytest.fixture
def app(config: ServerConfig):
    app = FastAPI()

    @app.post("/pub-sub/push")
    async def pub_sub_push(d: D):
        GcpTopic(config.response_topic_name).publish(d)
        return d

    return app


@pytest.fixture
def client(app: FastAPI) -> ApiTestClient:  # type: ignore
    yield ApiTestClient(app)  # type: ignore


def test_subscription_factory(client: ApiTestClient, subscription_factory: SubscriptionFactory, config: ServerConfig):
    # Given: A subscription created by factory
    resp_sub = subscription_factory(config.response_topic_name, D)
    # And: A subscription emulator is run
    with resp_sub.run_push_emulator(client, "/pub-sub/push") as sub_emulator:
        # When: A message is published
        d = D(name="foo", value="bar")
        GcpTopic(config.response_topic_name).publish(d)
        # Then: It is received by the emulator
        while not sub_emulator.isfinished(timeout=120, expected_responses=1):
            time.sleep(0.1)
        # And: The payload is correct
        ret = sub_emulator.get_payloads()[0]
        assert ret == d
```
