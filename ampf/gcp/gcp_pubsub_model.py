import base64
import logging
from typing import Literal, Self

from google.cloud.pubsub_v1.subscriber.message import Message
from pydantic import BaseModel

from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.base_topic import BaseTopic
from ampf.shared.pubsub_message import PubsubMessage, PubsubRequest

from .gcp_topic import GcpTopic

_log = logging.getLogger(__name__)


class GcpPubsubRequest(PubsubRequest):
    """Represents a request received from a Pub/Sub subscription with Push method."""

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
            message=PubsubMessage(
                messageId=message.message_id,
                attributes=message.attributes,  # type: ignore
                data=base64.b64encode(message.data).decode("utf-8"),
            ),
            subscription=subscription,
        )

    def set_default_response_topic(self, topic_name: str) -> None:
        """Sets the default response topic in the message attributes.
        A current payload is sent to this topic if response topic is
        not specified in message attributes.

        Args:
            topic_name: The name of the default topic to set.
        """
        if not self.message.attributes:
            self.message.attributes = {}
        if "response_topic" not in self.message.attributes:
            self.message.attributes["response_topic"] = topic_name
            _log.debug("Set default response topic: %s", topic_name)

    def set_response_topic(self, topic_name: str) -> None:
        """Sets the topic to forward the current payload.

        Args:
            topic_name: The name of the default topic to set.
        """
        if not self.message.attributes:
            self.message.attributes = {}
        self.message.attributes["response_topic"] = topic_name
        _log.debug("Response topic: %s", topic_name)

    def forward_response_to_topic(self, topic_name: str) -> None:
        """Sets the topic to forward the response payload.

        Args:
            topic_name: The name of the default topic to set.
        """
        if not self.message.attributes:
            self.message.attributes = {}
        self.message.attributes["forward_to__topic"] = topic_name
        _log.debug("Set forward to topic: %s", topic_name)

    def publish_response(
        self,
        response: BaseModel,
        default_topic_name: str | None = None,
        factory: BaseAsyncFactory | None = None,
    ) -> None:
        """Publishes a response to a specified topic. Topic can be specified in the message attributes or defaults to a provided topic name.
        If `sender_id` is provided in the message attributes, it will be published with the response.

        Args:
            response: The response to publish.
            default_topic_name: The name of the default topic to publish the response to.
            factory: Optional AsyncFactory to create the topic.
        """
        if self.message.attributes:
            response_topic_name = self.message.attributes.get("response_topic")
            sender_id = self.message.attributes.get("sender_id")
        else:
            response_topic_name = default_topic_name
            sender_id = None

        if self.message.attributes and "forward_to__topic" in self.message.attributes:
            forward_topic_name = self.message.attributes["forward_to__topic"]
            _log.debug("Publishing response to topic: %s", forward_topic_name)
            attributes = {}
            if sender_id:
                attributes["sender_id"] = sender_id
            if response_topic_name:
                attributes["response_topic"] = response_topic_name
            topic = self.create_topic(forward_topic_name, factory)
            topic.publish(response, attributes)
            _log.debug("Response sent to topic: %s", response_topic_name, extra={"attributes": attributes})
        elif response_topic_name:
            _log.debug("Publishing response to topic: %s", response_topic_name)
            attributes = {"sender_id": sender_id} if sender_id else None
            topic = self.create_topic(response_topic_name, factory)
            topic.publish(response, attributes)
            _log.debug("Response sent to topic: %s", response_topic_name, extra={"attributes": attributes})

    def create_topic(self, topic_name: str, factory: BaseAsyncFactory | None = None) -> BaseTopic:
        if factory:
            return factory.create_topic(topic_name)
        else:
            return GcpTopic(topic_name)

    async def publish_response_async(
        self,
        factory: BaseAsyncFactory,
        response: BaseModel,
        default_topic_name: str | None = None,
    ) -> None:
        """Publishes a response to a specified topic. Topic can be specified in the message attributes or defaults to a provided topic name.
        If `sender_id` is provided in the message attributes, it will be published with the response.

        Args:
            factory: AsyncFactory to create the topic and publish the message.
            response: The response to publish.
            default_topic_name: The name of the default topic to publish the response to.
        """
        attributes = self.message.attributes or {}
        response_topic = attributes.get("response_topic", default_topic_name)
        topic_name = attributes.get("forward_to__topic", response_topic)
        if "forward_to__topic" not in attributes:
            response_topic = None
        sender_id = attributes.get("sender_id")

        if topic_name:
            _log.debug("Publishing response to topic: %s", topic_name)
            messageId = await factory.publish_message(
                topic_name, response, response_topic=response_topic, sender_id=sender_id
            )
            _log.debug("Response sent to topic: %s, messageId: %s", topic_name, messageId)


class GcpPubsubResponse(BaseModel):
    """Represents a response sent to a Pub/Sub subscription with Push method."""

    status: Literal["acknowledged"]
    messageId: str | None = None

    @classmethod
    def create(cls, message_id: str | None = None) -> Self:
        return cls(status="acknowledged", messageId=message_id)
