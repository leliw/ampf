from ampf.gcp.gcp_async_factory import GcpAsyncFactory


def test_create_topic(gcp_async_factory: GcpAsyncFactory):
    # Given: A topic_id
    topic_id = "test_topic"
    # When: Create topic
    topic = gcp_async_factory.create_topic(topic_id)
    # Then: Topic is created
    assert topic.topic_id == topic_id
