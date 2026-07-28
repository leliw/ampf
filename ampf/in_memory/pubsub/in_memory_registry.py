from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Importy wykonywane wyłącznie przez narzędzia do analizy typów (np. IDE, mypy)
if TYPE_CHECKING:
    from ampf.in_memory.pubsub.in_memory_subscription import InMemorySubscription
    from ampf.in_memory.pubsub.in_memory_subscription_pull import InMemorySubscriptionPull
    from ampf.in_memory.pubsub.in_memory_topic import InMemoryTopic

_log = logging.getLogger(__name__)


class MemoryPubsubRegistry:
    _topics: dict[str, InMemoryTopic] = {}
    _all_subscriptions: dict[str, InMemorySubscription | InMemorySubscriptionPull] = {}
    _subscriptions_by_topic: dict[str, list[InMemorySubscription | InMemorySubscriptionPull]] = {}
    _bindings: dict[str, str] = {}  # subscription_id -> topic_id

    @classmethod
    def reset(cls):
        """Resetuje stan rejestru pomiędzy testami."""
        cls._topics.clear()
        cls._all_subscriptions.clear()
        cls._subscriptions_by_topic.clear()
        cls._bindings.clear()
        _log.debug("MemoryPubSubRegistry reset")

    @classmethod
    def register_topic(cls, topic: InMemoryTopic):
        cls._topics[topic.topic_id] = topic
        _log.debug("Registered memory topic: %s", topic.topic_id)

    @classmethod
    def register_subscription(cls, subscription: InMemorySubscription | InMemorySubscriptionPull):
        sub_id = subscription.subscription_id
        cls._all_subscriptions[sub_id] = subscription
        _log.debug("Registered memory subscription: %s", sub_id)

        # Jeśli subskrypcja jest już powiązana z tematem, przypisz ją
        topic_id = cls._bindings.get(sub_id)
        if topic_id:
            cls._associate(subscription, topic_id)

    @classmethod
    def bind(cls, subscription_id: str, topic_id: str):
        """Wiąże subskrypcję z tematem."""
        cls._bindings[subscription_id] = topic_id
        _log.debug("Bound subscription %s to topic %s", subscription_id, topic_id)

        subscription = cls._all_subscriptions.get(subscription_id)
        if subscription:
            cls._associate(subscription, topic_id)

    @classmethod
    def delete(cls, subscription_id: str):
        if subscription_id in cls._bindings:
            subscription = cls._bindings.pop(subscription_id)
        if subscription_id in cls._all_subscriptions:
            subscription = cls._all_subscriptions.pop(subscription_id)
        if subscription:
            for _, subs in list(MemoryPubsubRegistry._subscriptions_by_topic.items()):
                if subscription in subs:
                    subs.remove(subscription)

    @classmethod
    def _associate(cls, subscription: InMemorySubscription | InMemorySubscriptionPull, topic_id: str):
        if topic_id not in cls._subscriptions_by_topic:
            cls._subscriptions_by_topic[topic_id] = []
        if subscription not in cls._subscriptions_by_topic[topic_id]:
            cls._subscriptions_by_topic[topic_id].append(subscription)
            _log.debug("Associated subscription %s with topic %s", subscription.subscription_id, topic_id)

    @classmethod
    def get_subscriptions_for_topic(cls, topic_id: str) -> list[InMemorySubscription | InMemorySubscriptionPull]:
        return cls._subscriptions_by_topic.get(topic_id, [])
