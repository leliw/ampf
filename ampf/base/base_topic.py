from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel


class BaseTopic[T: BaseModel](ABC):
    """An abstract base class for a topic"""

    @abstractmethod
    def publish(
        self,
        data: T | str | bytes,
        attrs: Optional[Dict[str, str]] = None,
        response_topic: Optional[str] = None,
        sender_id: Optional[str] = None,
    ) -> str:
        """Publishes a message to the topic.

        Args:
            data: The message to publish.
            attrs: The attributes of the message.
        Returns:
            The message ID.
        """
        pass

    async def publish_async(
        self,
        data: T | str | bytes,
        attrs: Optional[Dict[str, str]] = None,
        response_topic: Optional[str] = None,
        sender_id: Optional[str] = None,
    ) -> str:
        """Publishes a message to the topic.

        Args:
            data: The message to publish.
            attrs: The attributes of the message.
        Returns:
            The message ID.
        """
        return self.publish(data, attrs, response_topic, sender_id)
