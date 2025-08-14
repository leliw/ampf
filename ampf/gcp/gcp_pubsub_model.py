import base64
import logging
from typing import Dict, Literal, Optional, Self, Type

from pydantic import BaseModel

from .gcp_topic import GcpTopic
from google.cloud.pubsub_v1.subscriber.message import Message


_log = logging.getLogger("ampf.gcp.gcp_pubsub")


class GcpPubsubMessage(BaseModel):
    """Represents a message received from a Pub/Sub subscription with Push method"""

    attributes: Optional[Dict[str, str]] = None
    data: str  # Base64 encoded message
    messageId: Optional[str] = None
    publishTime: Optional[str] = None

    @classmethod
    def create(cls, data: BaseModel, attributes: Optional[Dict[str, str]] = None) -> Self:
        """Creates a GcpPubsubMessage from a Pydantic model (useful for testing purposes).

        Args:
            data: The Pydantic model to serialize.
            attributes: The attributes to include in the message.
        Returns:
            The created GcpPubsubMessage.
        """
        return cls(attributes=attributes, data=base64.b64encode(data.model_dump_json().encode("utf-8")).decode("utf-8"))


class GcpPubsubRequest(BaseModel):
    """Represents a request received from a Pub/Sub subscription with Push method."""

    message: GcpPubsubMessage
    subscription: str

    @classmethod
    def create(
        cls, data: BaseModel, attributes: Optional[Dict[str, str]] = None, subscription: str = "ignored"
    ) -> Self:
        """Creates a GcpPubsubRequest from a Pydantic model (useful for testing purposes).

        Args:
            data: The Pydantic model to serialize.
            attributes: The attributes to include in the message.
            subscription: The name of the subscription.
        Returns:
            The created GcpPubsubRequest.
        """
        return cls(message=GcpPubsubMessage.create(data, attributes), subscription=subscription)

    @classmethod
    def create_from_message(cls, message: Message, subscription: str = "ignored") -> Self:
        """Creates a GcpPubsubRequest from a Message object (useful for testing purposes).

        Args:
            message: The Message object to create the request from.
            subscription: The name of the subscription.
        Returns:
            The created GcpPubsubRequest.
        """
        return cls(
            message=GcpPubsubMessage(
                messageId=message.message_id,
                attributes=message.attributes,  # type: ignore
                data=base64.b64encode(message.data).decode("utf-8"),
            ),
            subscription=subscription,
        )

    def decoded_data[T: BaseModel](self, clazz: Type[T]) -> T:
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
        _log.debug("Decoded data: %s", decoded_data)
        return clazz.model_validate_json(decoded_data)

    def set_default_response_topic(self, topic_name: str) -> None:
        """Sets the default response topic in the message attributes.

        Args:
            topic_name: The name of the default topic to set.
        """
        if not self.message.attributes:
            self.message.attributes = {}
        if "response_topic" not in self.message.attributes:
            self.message.attributes["response_topic"] = topic_name
            _log.debug("Set default response topic: %s", topic_name)
            
    def publish_response(self, response: BaseModel, default_topic_name: Optional[str] = None) -> None:
        """Publishes a response to a specified topic. Topic can be specified in the message attributes or defaults to a provided topic name.
        If `sender_id` is provided in the message attributes, it will be published with the response.

        Args:
            response: The response to publish.
            default_topic_name: The name of the default topic to publish the response to.
        """
        if self.message.attributes:
            response_topic_name = self.message.attributes.get("response_topic")
            sender_id = self.message.attributes.get("sender_id")
        else:
            response_topic_name = default_topic_name
            sender_id = None

        if response_topic_name:
            _log.debug("Publishing response to topic: %s", response_topic_name)
            topic = GcpTopic(response_topic_name)
            _log.debug("Response: %s", response.model_dump_json())
            topic.publish(response, {"sender_id": sender_id} if sender_id else None)


class GcpPubsubResponse(BaseModel):
    """Represents a response sent to a Pub/Sub subscription with Push method."""

    status: Literal["acknowledged"]
    messageId: Optional[str] = None

    @classmethod
    def create(cls, message_id: Optional[str] = None) -> Self:
        return cls(status="acknowledged", messageId=message_id)