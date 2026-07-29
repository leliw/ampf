from abc import ABC, abstractmethod

from pydantic import BaseModel

from ampf.base.base_subscription import BaseSubscription


class BaseTopic[T: BaseModel](ABC):
    """An abstract base class for a topic"""

    @abstractmethod
    def publish(
        self,
        data: T | str | bytes,
        attrs: dict[str, str] | None = None,
        response_topic: str | None = None,
        sender_id: str | None = None,
    ) -> str:
        """Publishes a message to the topic.

        Args:
            data: The message to publish.
            attrs: The attributes of the message.
        Returns:
            The message ID.
        """
        ...
        
    async def publish_async(
        self,
        data: T | str | bytes,
        attrs: dict[str, str] | None = None,
        response_topic: str | None = None,
        sender_id: str | None = None,
    ) -> str:
        """Publishes a message to the topic.

        Args:
            data: The message to publish.
            attrs: The attributes of the message.
        Returns:
            The message ID.
        """
        return self.publish(data, attrs, response_topic, sender_id)

    @abstractmethod
    def create_subscription[R: BaseModel](
        self,
        subscription_id: str | None = None,
        clazz: type[R] | None = None,
        processing_timeout: float = 5.0,
        per_message_timeout: float = 1.0,
        exist_ok: bool = False,
    ) -> BaseSubscription[R]:
        pass
