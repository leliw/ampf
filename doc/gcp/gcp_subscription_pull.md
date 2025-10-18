# GcpSubscriptionPull

A pull subscription for GCP Pub/Sub that allows processing messages with a callback. It operates in the background,
listening for messages and invoking the user-defined callback for each message received.

## Constructor

Arguments:

* `subscription_id: str` - The ID of the Pub/Sub subscription.
* `project_id: Optional[str] = None` - The GCP project ID. If not provided, the default project will be used.
* `clazz: Optional[Type[T]] = None` - The Pydantic model class for decoding messages. If not provided, raw messages will be used.
* `loop: Optional[asyncio.AbstractEventLoop] = None` - The asyncio event loop to run the subscription in. If not provided, the default event loop will be used.
* `subscriber: Optional[SubscriberClient] = None` - An optional SubscriberClient instance. If not provided, a new instance will be created.

## Methods

* `run_and_exit(self, processing_timeout: float = 5.0, per_message_timeout: float = 1.0) -> None` - Runs the subscription, processes messages, and then exits. It should be used in jobs triggered by instance, e.g. Cloud Functions or Cloud Run Jobs
* `run(self, per_message_timeout: float = 1.0):` - Runs the subscription, processes messages till the signal `SIGTERM` is received. It can be used with FastAPI application.
* `callback(self, request: GcpPubsubRequest) -> bool:` - It is called for each message received. If it returns `True`, the message is acknowledged. Otherwise, it is negatively acknowledged. By default, it calls `callback_async` in an event loop.
* `callback_async(self, request: GcpPubsubRequest) -> bool:` - Abstract method that needs to be implemented by the user. It is called for each message received. If it returns `True`, the message is acknowledged. Otherwise, it is negatively acknowledged.

## Usage

### Run alongside FastAPI application

Run subscription alongside FastAPI application using lifespan event:

```python
def lifespan(config: ServerConfig = ServerConfig()):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.async_factory = GcpAsyncFactory(bucket_name=config.gcp_bucket_name)
        app.state.config = config
        _log.info("Version: %s", config.version)
        if config.gcp_subscription_name:
            _log.info("Subscription: %s", config.gcp_subscription_name)
            loop = asyncio.get_running_loop()
            subscription = SubscriptionPull(CrawlerService(), app.state.async_factory, config.gcp_subscription_name, loop)
            subscription.run()
        else:
            subscription = None
        yield
        if subscription:
            subscription.stop()

    return lifespan
```

Testing - just run the application and send messages to the subscription.

```python
@pytest.fixture
def app(config):
    app = main_app
    # Reconfigure the lifespan to use the test server config
    app.router.lifespan_context = lifespan(config)
    return app


@pytest.fixture
def client(app) -> TestClient: # type: ignore
    with TestClient(app) as client:
        yield client # type: ignore

def test_subscription_pull(
    log: logging.Logger,
    client: ApiTestClient,
    config: ServerConfig,
    topic: GcpTopic,
    topic2: GcpTopic,
    subscription2: GcpSubscription[CrawlResult],
):
    log.info("Test started")
    # Given: A configuration with gcp subscription name
    assert config.gcp_subscription_name
    # And: An apllication running
    assert client
    # And: A url request
    req = UrlResourcesRequest(resources=[UrlResourceRequest(url="https://example.com")])

    # When: The request is published with response topic
    topic.publish(req, response_topic=topic2.topic_id)

    # Then: A response is published
    ret = next(subscription2.__iter__())
    assert isinstance(ret, CrawlResult)
    assert ret.url == "https://example.com"
    assert ret.content
    assert "Example Domain" in ret.content
    log.info("Test passed")
```

### Run as a job that processes messages and then exits

```python
async def run(config: ServerConfig = ServerConfig(), loop: Optional[asyncio.AbstractEventLoop] = None):
    """Run the Pub/Sub subscription pull worker."""
    if not config.gcp_subscription_name:
        raise ValueError("GCP subscription name is not set in the configuration")
    async_factory = GcpAsyncFactory(bucket_name=config.gcp_bucket_name)
    async with CrawlerService() as crawler_service:
        subscription = SubscriptionPull(
            crawler_service, async_factory, config.gcp_subscription_name, loop or asyncio.get_event_loop()
        )
        _log.info("Starting subscription pull worker")
        await subscription.run_and_exit(processing_timeout=config.gcp_subscription_timeout)
        _log.info("Subscription pull worker stopped")
    # concurrent.futures.thread._threads_queues.clear()  # type: ignore
```

Testing - run the worker in the background and publish messages to the subscription.

```python
@pytest.mark.asyncio
async def test_worker(
    log: logging.Logger,
    config: ServerConfig,
    topic: GcpTopic,
    topic2: GcpTopic,
    subscription2: GcpSubscription[CrawlResult],
):
    log.info("Test started")
    # Given: A configuration with gcp subscription name
    assert config.gcp_subscription_name
    # And: A worker running in the background.
    loop = asyncio.get_running_loop()
    worker_task = asyncio.create_task(worker.run(config, loop))
    await asyncio.sleep(1)  # Give the worker a moment to start up and listen to the subscription.
    # And: A url request
    req = UrlResourcesRequest(resources=[UrlResourceRequest(url="https://example.com")])

    # When: The request is published with response topic
    _log.info("Publishing message")
    await topic.publish_async(req, response_topic=topic2.topic_id)

    # Then: A response with scrapped page is published.
    _log.info("Waiting for message")
    ret = await asyncio.to_thread(lambda: next(iter(subscription2), None))
    _log.info("Message received")
    assert isinstance(ret, CrawlResult)
    assert ret.url == "https://example.com"
    assert ret.content
    assert "Example Domain" in ret.content

    # Wait for the worker task to finish.
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # await asyncio.wait_for(worker_task, timeout=30)
    log.info("Test passed")
```
