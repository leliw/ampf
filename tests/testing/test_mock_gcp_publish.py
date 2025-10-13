from pydantic import BaseModel

from ampf.gcp.gcp_topic import GcpTopic
from ampf.testing.mock_gcp_publish import MockGcpPublish


class D(BaseModel):
    name: str
    value: str


def test_my_function_with_pubsub(mock_gcp_publish: MockGcpPublish):
    # Given: A MockGcpPublish as fixture
    # When: Some publish is called
    GcpTopic("my-topic").publish(D(name="foo", value="bar"))
    # Then: It is captured and can be asserted

    # Assert that publish was called
    mock_gcp_publish.assert_called_once()
    # Assert that topic is correct
    mock_gcp_publish.assert_topic("my-topic")
    # Assert that payload is correct
    payload = mock_gcp_publish.get_payload(D)
    assert payload.name == "foo"
    assert payload.value == "bar"
