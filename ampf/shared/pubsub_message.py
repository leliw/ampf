import base64
import logging
from datetime import UTC, datetime
from typing import Self
from uuid import uuid4

from pydantic import BaseModel

_log = logging.getLogger(__name__)


class PubsubMessage(BaseModel):
    """Represents a message received from a Pub/Sub subscription with Push method"""

    attributes: dict[str, str] | None = None
    data: str
    messageId: str
    publishTime: str | None = None

    @classmethod
    def create(cls, data: BaseModel, attributes: dict[str, str] | None = None) -> Self:
        """Creates a GcpPubsubMessage from a Pydantic model (useful for testing purposes).

        Args:
            data: The Pydantic model to serialize.
            attributes: The attributes to include in the message.
        Returns:
            The created GcpPubsubMessage.
        """
        return cls(
            attributes=attributes,
            data=base64.b64encode(data.model_dump_json().encode("utf-8")).decode("utf-8"),
            messageId=uuid4().hex,
            publishTime=str(datetime.now(UTC)),
        )

    def decoded_data[T: BaseModel](self, clazz: type[T]) -> T:
        """Decodes the message data from base64 and deserializes it into a Pydantic model.

        Args:
            clazz: The Pydantic model class to deserialize the data into.
        Returns:
            The deserialized Pydantic model.
        """
        encoded_data = self.data
        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
        return clazz.model_validate_json(decoded_data)


class PubsubRequest(BaseModel):
    """Represents a request received from a Pub/Sub subscription with Push method."""

    message: PubsubMessage
    subscription: str

    @classmethod
    def create(
        cls,
        data: BaseModel,
        attributes: dict[str, str] | None = None,
        subscription: str = "ignored",
        response_topic: str | None = None,
        sender_id: str | None = None,
    ) -> Self:
        """Creates a GcpPubsubRequest from a Pydantic model (useful for testing purposes).

        Args:
            data: The Pydantic model to serialize.
            attributes: The attributes to include in the message.
            subscription: The name of the subscription.
        Returns:
            The created GcpPubsubRequest.
        """
        if attributes is None:
            attributes = {}
        if response_topic:
            attributes["response_topic"] = response_topic
        if sender_id:
            attributes["sender_id"] = sender_id
        return cls(message=PubsubMessage.create(data, attributes), subscription=subscription)

    def decoded_data[T: BaseModel](self, clazz: type[T]) -> T:
        """Decodes the message data from base64 and deserializes it into a Pydantic model.

        Args:
            clazz: The Pydantic model class to deserialize the data into.
        Returns:
            The deserialized Pydantic model.
        """
        encoded_data = self.message.data
        decoded_data = base64.b64decode(encoded_data).decode("utf-8")

        # Log subscription and message ID
        _log.info(
            "Received message from subscription: %s, ID: %s",
            self.subscription,
            self.message.messageId,
        )
        return clazz.model_validate_json(decoded_data)


# class PubsubMessage:
#     def __init__(self, message_id: str, data: str, attributes: dict[str, str]):
#         self.message_id = message_id
#         self.messageId = message_id
#         self.data = data
#         self.attributes = attributes
#         self.publish_time = datetime.now(UTC)
#         self._acked = False
#         self._nacked = False

#     def ack(self):
#         self._acked = True

#     def nack(self):
#         self._nacked = True

#     @property
#     def acked(self) -> bool:
#         return self._acked

#     @property
#     def nacked(self) -> bool:
#         return self._nacked
