import asyncio
import logging
import signal

import pytest
from pydantic import BaseModel

from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest
from ampf.gcp.gcp_subscription import GcpSubscription
from ampf.gcp.gcp_subscription_pull import GcpSubscriptionPull
from ampf.gcp.gcp_topic import GcpTopic


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
    sub = GcpSubscriptionPull(subscription.subscription_id, subscription.project_id)
    assert sub.is_empty()
    # When: Run and exit with 1 sec timeout
    await sub.run_and_exit(1)
    # Then: Subscription is empty
    assert sub.is_empty()


@pytest.mark.asyncio
async def test_run_and_exit_with_message(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, subscription.project_id)
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
    # And: Run and exit with 1 sec timeout
    await sub.run_and_exit(1)

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The message was processed
    assert called


@pytest.mark.asyncio
async def test_run_and_exit_timeout(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, subscription.project_id)
    assert sub.is_empty()
    # And: Defined callback
    called = 0

    def callback(request: GcpPubsubRequest):
        print("Callback called")
        nonlocal called
        called += 1
        return True

    sub.callback = callback

    # When: 4 messages are sent with 0.5 sec sleep and run and exit with 1 sec timeout
    async def send_messages():
        await asyncio.sleep(0.2)
        topic.publish("test1")
        print("test1")
        await asyncio.sleep(0.5)
        topic.publish("test2")
        print("test2")
        await asyncio.sleep(0.5)
        topic.publish("test3")
        print("test3")
        await asyncio.sleep(0.5)
        topic.publish("test4")
        print("test4")

    print("Starting")
    await asyncio.gather(asyncio.create_task(send_messages()), asyncio.create_task(sub.run_and_exit(1.0, 0.1)))
    print("Finished")

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The messages were processed
    assert called == 4


@pytest.mark.asyncio
async def test_run_and_sigterm_with_message(topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, subscription.project_id)
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
    sub = GcpSubscriptionPull(subscription.subscription_id, subscription.project_id)
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
    # And: Run and exit with 1 sec timeout
    await sub.run_and_exit(1)

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The message was processed
    assert called


@pytest.mark.asyncio
async def test_callback_async(log: logging.Logger, topic: GcpTopic, subscription: GcpSubscription):
    # Given: An empty Pub/Sub subcription
    sub = GcpSubscriptionPull(subscription.subscription_id, subscription.project_id)
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
        await asyncio.sleep(0.2)
        topic.publish(D(name="test1"))
        await asyncio.sleep(0.5)
        topic.publish(D(name="test2"))
        await asyncio.sleep(0.5)
        topic.publish(D(name="test3"))
        await asyncio.sleep(0.5)
        topic.publish(D(name="test4"))

    await asyncio.gather(asyncio.create_task(send_messages()), asyncio.create_task(sub.run_and_exit(1.0, 0.1)))

    # Then: Subscription is empty
    assert sub.is_empty()
    # And: The messages were processed
    assert called == 4
