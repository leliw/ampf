import types
from concurrent.futures import Future
from typing import Type
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel


class MockGcpPublish(MagicMock):
    def assert_topic(self: MagicMock, response_topic: str, index: int = 0) -> None:
        pass

    def get_payload[T: BaseModel](self: MagicMock, clazz: Type[T], index: int = 0) -> T:  # type: ignore
        pass


@pytest.fixture
def mock_gcp_publish() -> MockGcpPublish:  # type: ignore
    """Fixture that mocks GCP Pub/Sub publish method.
    It provides helper methods `assert_topic` and `get_payload` for easier testing.
    """

    def assert_topic(self: MagicMock, response_topic: str, index: int = 0):
        """Assert that the mock was called with a topic ending in response_topic."""
        args, _ = self.call_args_list[index]
        actual_topic = args[0]
        assert actual_topic.endswith(response_topic)

    def get_payload[T: BaseModel](self: MagicMock, clazz: Type[T], index: int = 0) -> T:
        args, _ = self.call_args_list[index]
        bdata: bytes = args[1]
        assert bdata
        data = clazz.model_validate_json(bdata.decode("utf-8"))
        return data

    # Patch the PublisherClient.publish method to mock GCP publish
    with patch("google.cloud.pubsub_v1.PublisherClient.publish") as mock_publish:
        mock_future = Future()
        mock_future.set_result("mock-message-id-123")
        mock_publish.return_value = mock_future
        mock_publish.assert_topic = types.MethodType(assert_topic, mock_publish)
        mock_publish.get_payload = types.MethodType(get_payload, mock_publish)
        yield mock_publish  # type: ignore
