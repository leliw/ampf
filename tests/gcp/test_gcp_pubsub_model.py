import pytest
from pydantic import BaseModel

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest


class D(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_request_publish_response_async(async_factory: BaseAsyncFactory, mock_method):
    mocker_publish = mock_method(BaseAsyncFactory.publish_message)
    # Given: A request
    req = GcpPubsubRequest.create(data=D(name="test"), response_topic="response_topic")
    # And: A response
    resp = D(name="response")
    # When: The response is published
    await req.publish_response_async(async_factory, resp)
    # Then:
    mocker_publish.assert_called_once_with("response_topic", resp, sender_id=None)
