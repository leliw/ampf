import pytest
from pydantic import BaseModel

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest
from ampf.testing.mock_method import MockMethod


class D(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_request_publish_response_async(async_factory: BaseAsyncFactory, mock_method: MockMethod):
    publish_mock = mock_method(BaseAsyncFactory.publish_message)
    # Given: A request
    req = GcpPubsubRequest.create(data=D(name="test"), response_topic="response_topic")
    # And: A response
    resp = D(name="response")
    # When: The response is published
    await req.publish_response_async(async_factory, resp)
    # Then: A publish method is called
    publish_mock.assert_called_once_with("response_topic", resp, response_topic=None, sender_id=None)


@pytest.mark.asyncio
async def test_request_forward_response_async(async_factory: BaseAsyncFactory, mock_method: MockMethod):
    publish_mock = mock_method(BaseAsyncFactory.publish_message)
    # Given: A request
    req = GcpPubsubRequest.create(data=D(name="test"), response_topic="response_topic")
    # And: A response
    resp = D(name="response")
    # And: The response is forwarded
    req.forward_response_to_topic("forward_topic")
    # When: The response is published
    await req.publish_response_async(async_factory, resp)
    # Then: A response is published in forward_topic with response_topic
    publish_mock.assert_called_once_with("forward_topic", resp, response_topic="response_topic", sender_id=None)