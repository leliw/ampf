import asyncio
import logging
import signal
import time
from types import CoroutineType
from typing import Any
from uuid import uuid4

import pytest
from google.api_core.exceptions import InvalidArgument
from pydantic import BaseModel

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest
from ampf.gcp.gcp_subscription import GcpSubscription
from ampf.gcp.gcp_subscription_pull import GcpSubscriptionPull
from ampf.gcp.gcp_topic import GcpTopic
from ampf.gcp.subscription_processor import SubscriptionProcessor
from ampf.testing.mock_method import MockMethod


@pytest.fixture(scope="session")
def log() -> logging.Logger:
    logging.getLogger("").setLevel(logging.INFO)
    logging.getLogger("processors").setLevel(logging.DEBUG)
    logging.getLogger("haintech.pipelines").setLevel(logging.DEBUG)
    logging.getLogger("markdown_pages_pre_processor").setLevel(logging.DEBUG)
    logging.getLogger("ampf.gcp").setLevel(logging.DEBUG)
    log = logging.getLogger("test")
    log.setLevel(logging.DEBUG)
    return log


@pytest.mark.asyncio
async def test_run_and_exit_empty(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, project_id=subscription.project_id)
    assert sub.is_empty()
    # When: Run and exit with 1 sec timeout
    await sub.run_and_exit(1)
    # Then: Subscription is empty
    assert sub.is_empty()


@pytest.mark.asyncio
async def test_not_existing():
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(uuid4().hex)
    # When: Run pull subscription
    # Then: Exception is raised
    with pytest.raises(InvalidArgument) as e:
        await sub.run_and_exit(3)
    assert "Invalid resource name" in str(e)


@pytest.mark.asyncio
async def test_run_and_exit_with_message(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, project_id=subscription.project_id)
    assert sub.is_empty()
    # And: Defined callback
    called = False

    def callback(request: GcpPubsubRequest):
        nonlocal called
        called = True
        return True

    sub.callback = callback

    # When: A message is sent
    topic.publish("test")
    # And: Run and exit with 2 sec timeout
    await sub.run_and_exit(2)

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The message was processed
    assert called


@pytest.mark.asyncio
async def test_run_and_exit_timeout(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, project_id=subscription.project_id)
    assert sub.is_empty()
    # And: Defined callback
    called = 0

    def callback(request: GcpPubsubRequest):
        print("Callback called")
        nonlocal called
        called += 1
        return True

    sub.callback = callback

    # When: 4 messages are sent with 0.5 sec sleep and run and exit with 2 sec timeout
    async def send_messages():
        await asyncio.sleep(0.4)
        await topic.publish_async("test1")
        await asyncio.sleep(1.0)
        await topic.publish_async("test2")
        await asyncio.sleep(1.0)
        await topic.publish_async("test3")
        await asyncio.sleep(1.0)
        await topic.publish_async("test4")

    print("Starting")
    await asyncio.gather(send_messages(), sub.run_and_exit(2.0, 0.2))
    print("Finished")

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The messages were processed
    assert called == 4


@pytest.mark.asyncio
async def test_run_and_sigterm_with_message(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, project_id=subscription.project_id)
    assert sub.is_empty()
    # And: Defined callback
    called = False

    def callback(request: GcpPubsubRequest):
        nonlocal called
        called = True
        return True

    sub.callback = callback

    # When: A message is sent
    await topic.publish_async("test")
    # And: Run
    sub.run()
    await asyncio.sleep(3)
    # And: SIGTERM is sent
    signal.raise_signal(signal.SIGTERM)

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The message was processed
    assert called


class D(BaseModel):
    name: str
    value: str = ""


@pytest.mark.asyncio
async def test_run_and_exit_with_response_topic(
    topic: GcpTopic, subscription: GcpSubscription, topic2: GcpTopic, subscription2: GcpSubscription
):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, project_id=subscription.project_id)
    assert sub.is_empty()
    # And: Defined callback
    called = False

    def callback(request: GcpPubsubRequest):
        nonlocal called
        called = True
        payload = request.decoded_data(D)
        assert payload.name == "test"
        assert payload.value == "test"
        return True

    sub.callback = callback

    # When: A message is sent
    topic.publish(D(name="test", value="test"), response_topic=topic2.topic_id)
    # And: Run and exit with 2 sec timeout
    await sub.run_and_exit(2)

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The message was processed
    assert called


@pytest.mark.asyncio
async def test_callback_async(log: logging.Logger, topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, project_id=subscription.project_id)
    assert sub.is_empty()
    # And: Defined callback
    called = 0

    async def callback_async(request: GcpPubsubRequest):
        log.debug("Callback called %s", request.message.messageId)
        nonlocal called
        called += 1
        return True

    sub.callback_async = callback_async

    # When: 4 messages are sent with 0.5 sec sleep and run and exit with 1 sec timeout
    async def send_messages():
        await asyncio.sleep(0.4)
        await topic.publish_async(D(name="test1"))
        await asyncio.sleep(1.0)
        await topic.publish_async(D(name="test2"))
        await asyncio.sleep(1.0)
        await topic.publish_async(D(name="test3"))
        await asyncio.sleep(1.0)
        await topic.publish_async(D(name="test4"))

    log.debug("Starting")
    await asyncio.gather(sub.run_and_exit(1.2, 0.1), send_messages())
    log.debug("Finished")

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The messages were processed
    assert called == 4


class Out(BaseModel):
    name: str


class DProcessor(SubscriptionProcessor[D]):
    async def process_payload(self, payload: D) -> Out:
        return Out(name=payload.name)


@pytest.mark.asyncio
async def test_run_and_exit_with_processor(
    async_factory: BaseAsyncFactory,
    topic: GcpTopic,
    subscription: GcpSubscription,
    mock_method: MockMethod,
):
    mocker_publish = mock_method(BaseAsyncFactory.publish_message)
    # Given: A processor
    processor = DProcessor(async_factory, D)
    # And: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, processor=processor, project_id=subscription.project_id)
    assert sub.is_empty()
    # When: A message is sent
    await topic.publish_async(D(name="test", value="test"), response_topic="response_topic")
    # And: Run and exit with 2 sec timeout
    await sub.run_and_exit(2)

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The message was processed by the processor
    mocker_publish.assert_called_once_with("response_topic", Out(name="test"), response_topic=None, sender_id=None)


@pytest.mark.asyncio
async def test_callback_async_concurrent_1(log: logging.Logger, topic: GcpTopic, subscription: GcpSubscription):
    # Given: Parameter max concurrent messages
    max_concurrent_messages = 1
    # And: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(
        subscription.subscription_id,
        project_id=subscription.project_id,
        max_concurrent_messages=max_concurrent_messages,
    )
    assert sub.is_empty()
    # And: Defined callback
    called = 0

    async def callback_async(request: GcpPubsubRequest):
        log.debug("Callback called %s", request.message.messageId)
        nonlocal called
        called += 1
        await asyncio.sleep(0.5)
        return True

    sub.callback_async = callback_async

    # When: 4 messages are sent and subscription run and exit with 0.5 sec timeout
    calls = 4
    start_time = time.time()
    await asyncio.gather(
        sub.run_and_exit(1.5, 0.1), *[topic.publish_async(D(name=f"test{i + 1}")) for i in range(calls)]
    )
    end_time = time.time()

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The messages were processed
    assert called == calls
    # And: The processing took at least 2 seconds (+ subscription timeout) due to concurrency limit
    assert end_time - start_time >= float(calls / 2) + 1.5


@pytest.mark.asyncio
async def test_callback_async_concurrent_4(log: logging.Logger, topic: GcpTopic, subscription: GcpSubscription):
    # Given: Parameter max concurrent messages
    max_concurrent_messages = 4
    # And: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(
        subscription.subscription_id,
        project_id=subscription.project_id,
        max_concurrent_messages=max_concurrent_messages,
    )
    assert sub.is_empty()
    # And: Defined callback
    called = 0

    async def callback_async(request: GcpPubsubRequest):
        log.debug("Callback called %s", request.message.messageId)
        nonlocal called
        called += 1
        await asyncio.sleep(0.5)
        return True

    sub.callback_async = callback_async

    # When: 4 messages are sent and subscription run and exit with 0.5 sec timeout
    calls = 4
    tasks: list[CoroutineType[None, None, Any]] = [topic.publish_async(D(name=f"test{i + 1}")) for i in range(calls)]
    start_time = time.time()
    await asyncio.gather(sub.run_and_exit(1.5, 0.1), *tasks)
    end_time = time.time()

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The messages were processed
    assert called == calls
    # And: The processing took at max 2 seconds (+ subscription timeout) due to lack of concurrency limit
    assert end_time - start_time <= float(calls / 2) + 1.5
