import pytest
from pydantic import BaseModel

from ampf.gcp.gcp_async_factory import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic


def test_create_topic(gcp_async_factory: GcpAsyncFactory):
    # Given: A topic_id
    topic_id = "test_topic"
    # When: Create topic
    topic = gcp_async_factory.create_topic(topic_id)
    # Then: Topic is created
    assert topic.topic_id == topic_id


class D(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_publish_message(gcp_async_factory: GcpAsyncFactory, mock_method):
    publish_mocker = mock_method(GcpTopic.publish_async)
    # Given: A topic_id
    topic_id = "test_topic"
    # And: A message
    message = D(name="test")
    # When: I publish the message
    await gcp_async_factory.publish_message(topic_id, message)
    # Then: A message is published
    publish_mocker.assert_called_once_with(message, response_topic=None, sender_id=None)


def test_create_blob_location_with_bucket(gcp_async_factory: GcpAsyncFactory):
    # Given: A bucket name
    bucket_name = "test_bucket"
    # When: Create blob location
    blob_location = gcp_async_factory.create_blob_location("test_blob", bucket_name)
    # Then: Blob location is created
    assert blob_location.bucket == bucket_name
    assert blob_location.name == "test_blob"


def test_create_blob_location_without_bucket(gcp_async_factory: GcpAsyncFactory):
    # Given: A factory with bucket_name
    assert gcp_async_factory.bucket_name is not None
    # When: Create blob location
    blob_location = gcp_async_factory.create_blob_location("test_blob")
    # Then: Blob location is created
    assert blob_location.bucket == gcp_async_factory.bucket_name
    assert blob_location.name == "test_blob"
