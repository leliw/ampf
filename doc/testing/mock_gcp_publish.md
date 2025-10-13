# mock_gcp_publish

Fixture that mocks `publish` method of `google.cloud.pubsub_v1.PublisherClient`.

## Methods

* `assert_topic(self: MagicMock, response_topic: str, index: int = 0) -> None` - Asserts that the `publish` method was called with the specified topic at a given call index.
* `get_payload[T: BaseModel](self: MagicMock, clazz: Type[T], index: int = 0) -> T` - Retrieves and decodes the payload from a specific `publish` call, converting it to the specified Pydantic model.

If there were more than one call, use `index` parameter.

## Usage

Declare fixture in `conftest.py`

```python
from ampf.testing import *  # noqa: F403
```

Then import only `MockGcpPublish` class.

```python
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
```
