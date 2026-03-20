import asyncio
import logging

from pydantic import BaseModel

from ampf.gcp import GcpAsyncFactory, GcpSubscriptionPull, SubscriptionProcessor
from ampf.gcp.gcp_topic import GcpTopic

from .task_model import TaskRegistry, TaskRunner

_log = logging.getLogger(__name__)


class PubsubPullRunner(TaskRunner):
    def __init__(self, factory: GcpAsyncFactory, config: BaseModel):
        self.factory = factory
        self.config = config
        self._initialised = False
        self.topics: dict[str, GcpTopic] = {}
        self.subscriptions = {}

    def run(self, name: str, payload: BaseModel):
        if name not in self.topics:
            topic_name = self.get_topic_name(name)
            self.topics[name] = self.factory.create_topic(topic_name)
        message_id = self.topics[name].publish(payload)
        _log.info("Published message in topic %s with ID: %s", topic_name, message_id)

    async def run_async(self, name: str, payload: BaseModel):
        if name not in self.topics:
            topic_name = self.get_topic_name(name)
            self.topics[name] = self.factory.create_topic(topic_name)
        message_id = await self.topics[name].publish_async(payload)
        _log.info("Published message in topic %s with ID: %s", topic_name, message_id)

    @classmethod
    def create(cls, factory: GcpAsyncFactory, config: BaseModel) -> "PubsubPullRunner":
        return cls(factory, config)

    async def __aenter__(self):
        if not self._initialised:
            self._initialised = True
            loop = asyncio.get_running_loop()
            for task_name in TaskRegistry._tasks:
                processor_definition = TaskRegistry._tasks[task_name]
                subscription_name = self.get_subscription_name(task_name)
                _log.info("Starting subscription: %s", subscription_name)
                if processor_definition.payload_type is None:
                    raise ValueError("Payload type is required for task processor %s", task_name)
                s_processor = SubscriptionProcessor(self.factory, processor_definition.payload_type)
                s_processor.process_payload = processor_definition.processor # type: ignore
                subscription = GcpSubscriptionPull(subscription_name, s_processor, loop=loop)
                subscription.run()
                self.subscriptions[subscription_name] = subscription

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for name, subscription in self.subscriptions.items():
            _log.info("Stopping subscription: %s", name)
            subscription.stop()

    def get_topic_name(self, task_name: str) -> str:
        if hasattr(self.config, f"{task_name}_topic"):
            return getattr(self.config, f"{task_name}_topic")
        else:
            raise ValueError(f"Topic for task '{task_name}' not found in config")

    def get_subscription_name(self, task_name: str) -> str:
        if hasattr(self.config, f"{task_name}_subscription"):
            return getattr(self.config, f"{task_name}_subscription")
        else:
            raise ValueError(f"Subscription for task '{task_name}' not found in config")
