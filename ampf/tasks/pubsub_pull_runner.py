import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from ampf.gcp import GcpSubscriptionPull, SubscriptionProcessor
from ampf.gcp.gcp_async_factory import GcpAsyncFactory

from .pubsub_runner import PubsubRunner
from .task_registry import TaskRegistry

_log = logging.getLogger(__name__)


class PubsubPullRunner(PubsubRunner):

    def __init__(self, factory: GcpAsyncFactory, config: BaseModel):
        super().__init__(factory, config)
        self.subscriptions: dict[str, GcpSubscriptionPull] = {}

    @asynccontextmanager
    async def manage_lifecycle(self, _: FastAPI):
        if not self._initialized:
            self._initialized = True
            loop = asyncio.get_running_loop()
            for task_name, processor_definition in TaskRegistry._tasks.items():
                subscription_name = self.get_subscription_name(task_name)
                _log.info("Starting subscription: %s", subscription_name)
                if processor_definition.payload_type is None:
                    raise ValueError(f"Payload type is required for task processor {task_name}")
                s_processor = SubscriptionProcessor(self.factory, processor_definition.payload_type)
                s_processor.process_payload = lambda payload, tn=task_name: TaskRegistry.run_task_async(self, tn, payload)
                subscription = GcpSubscriptionPull(subscription_name, s_processor, loop=loop)
                subscription.run()
                self.subscriptions[subscription_name] = subscription

        yield self

        self._initialized = False
        for name, subscription in self.subscriptions.items():
            _log.info("Stopping subscription: %s", name)
            subscription.stop()
        self.subscriptions.clear()

    def get_subscription_name(self, task_name: str) -> str:
        if hasattr(self.config, f"{task_name}_subscription"):
            return getattr(self.config, f"{task_name}_subscription")
        else:
            raise ValueError(f"Subscription for task '{task_name}' not found in config")
