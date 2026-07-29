from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Importy wykonywane wyłącznie przez narzędzia do analizy typów (np. IDE, mypy)
if TYPE_CHECKING:
    from ampf.in_memory.pubsub.in_memory_subscription import InMemorySubscription
    from ampf.in_memory.pubsub.in_memory_subscription_pull import InMemorySubscriptionPull
    from ampf.in_memory.pubsub.in_memory_topic import InMemoryTopic

_log = logging.getLogger(__name__)


class InMemoryPubsubRegistry:

    def __init__(self) -> None:
        self._topics: dict[str, InMemoryTopic] = {}
        self._all_subscriptions: dict[str, InMemorySubscription | InMemorySubscriptionPull] = {}
        self._subscriptions_by_topic: dict[str, list[InMemorySubscription | InMemorySubscriptionPull]] = {}
        self._bindings: dict[str, str] = {}  # subscription_id -> topic_id

    def reset(self):
        """Resetuje stan rejestru pomiędzy testami."""
        self._topics.clear()
        self._all_subscriptions.clear()
        self._subscriptions_by_topic.clear()
        self._bindings.clear()
        _log.debug("InMemoryPubSubRegistry reset")

    def register_topic(self, topic: InMemoryTopic):
        self._topics[topic.topic_id] = topic
        _log.debug("Registered memory topic: %s", topic.topic_id)

    def register_subscription(self, subscription: InMemorySubscription | InMemorySubscriptionPull):
        sub_id = subscription.subscription_id
        self._all_subscriptions[sub_id] = subscription
        _log.debug("Registered memory subscription: %s", sub_id)

        # Jeśli subskrypcja jest już powiązana z tematem, przypisz ją
        topic_id = self._bindings.get(sub_id)
        if topic_id:
            self._associate(subscription, topic_id)

    def bind(self, subscription_id: str, topic_id: str):
        """Wiąże subskrypcję z tematem."""
        self._bindings[subscription_id] = topic_id
        _log.debug("Bound subscription %s to topic %s", subscription_id, topic_id)

        subscription = self._all_subscriptions.get(subscription_id)
        if subscription:
            self._associate(subscription, topic_id)

    def delete(self, subscription_id: str):
            self._bindings.pop(subscription_id, None)
            subscription = self._all_subscriptions.pop(subscription_id, None)
            if subscription:
                for _, subs in list(self._subscriptions_by_topic.items()):
                    if subscription in subs:
                        subs.remove(subscription)

    def _associate(self, subscription: InMemorySubscription | InMemorySubscriptionPull, topic_id: str):
        if topic_id not in self._subscriptions_by_topic:
            self._subscriptions_by_topic[topic_id] = []
        if subscription not in self._subscriptions_by_topic[topic_id]:
            self._subscriptions_by_topic[topic_id].append(subscription)
            _log.debug("Associated subscription %s with topic %s", subscription.subscription_id, topic_id)

    def get_subscriptions_for_topic(self, topic_id: str) -> list[InMemorySubscription | InMemorySubscriptionPull]:
        return self._subscriptions_by_topic.get(topic_id, [])
