import uuid
from typing import Self, override

from pydantic import BaseModel

from ampf.base.base_topic import BaseTopic

from ...shared.pubsub_message import PubsubMessage
from .in_memory_registry import MemoryPubsubRegistry
from .in_memory_subscription import InMemorySubscription


class InMemoryTopic[T: BaseModel](BaseTopic[T]):
    """Implementacja BaseTopic w pamięci do testów jednostkowych."""

    def __init__(self, topic_id: str):
        self.topic_id = topic_id
        self.published_messages: list[PubsubMessage] = []
        MemoryPubsubRegistry.register_topic(self)

    @override
    def publish(
        self,
        data: T | str,
        attrs: dict[str, str] | None = None,
        response_topic: str | None = None,
        sender_id: str | None = None,
    ) -> str:
        message_id = str(uuid.uuid4())

        final_attrs = attrs.copy() if attrs else {}
        if response_topic:
            final_attrs["response_topic"] = response_topic
        if sender_id:
            final_attrs["sender_id"] = sender_id

        if isinstance(data, BaseModel):
            data = data.model_dump_json()

        msg = PubsubMessage(message_id=message_id, data=data, attributes=final_attrs)
        self.published_messages.append(msg)

        # Dostarczenie wiadomości do wszystkich subskrypcji tego tematu
        subscriptions = MemoryPubsubRegistry.get_subscriptions_for_topic(self.topic_id)
        for sub in subscriptions:
            sub.put_message(msg)

        return message_id

    @override
    async def publish_async(
        self,
        data: T | str,
        attrs: dict[str, str] | None = None,
        response_topic: str | None = None,
        sender_id: str | None = None,
    ) -> str:
        # Publikacja w pamięci jest natychmiastowa i synchroniczna
        return self.publish(data, attrs, response_topic, sender_id)

    def exists(self) -> bool:
        return True

    def create(self, exist_ok: bool = False) -> Self:
        return self

    def delete(self) -> None:
        if self.topic_id in MemoryPubsubRegistry._topics:
            del MemoryPubsubRegistry._topics[self.topic_id]
        if self.topic_id in MemoryPubsubRegistry._subscriptions_by_topic:
            del MemoryPubsubRegistry._subscriptions_by_topic[self.topic_id]

    def create_subscription[R: BaseModel](
        self,
        subscription_id: str | None = None,
        clazz: type[R] | None = None,
        processing_timeout: float = 5.0,
        per_message_timeout: float = 1.0,
        exist_ok: bool = False,
    ) -> InMemorySubscription[R]:
        subscription_id = subscription_id or f"{self.topic_id}-sub"

        existing = MemoryPubsubRegistry._all_subscriptions.get(subscription_id)
        if existing:
            if exist_ok:
                return existing  # type: ignore
            raise ValueError(f"Subscription {subscription_id} already exists")

        sub = InMemorySubscription(
            subscription_id=subscription_id,
            topic=self,
            clazz=clazz,
            processing_timeout=processing_timeout,
            per_message_timeout=per_message_timeout,
        )
        MemoryPubsubRegistry.bind(subscription_id, self.topic_id)
        return sub
