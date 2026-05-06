import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Self

from fastapi import FastAPI
from pydantic import BaseModel

from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic

from .task_model import ManagedTaskRunner

_log = logging.getLogger(__name__)


class PubsubRunner(ManagedTaskRunner, ABC):
    def __init__(self, factory: GcpAsyncFactory, config: BaseModel):
        self.factory = factory
        self.config = config
        self._initialised = False
        self.topics: dict[str, GcpTopic] = {}
        self.subscriptions = {}

    def run(self, name: str, payload: BaseModel):
        topic = self.get_topic(name)
        message_id = topic.publish(payload)
        _log.info("Published message in topic %s with ID: %s", topic.topic_id, message_id)

    async def run_async(self, name: str, payload: BaseModel):
        topic = self.get_topic(name)
        message_id = await topic.publish_async(payload)
        _log.info("Published message in topic %s with ID: %s", topic.topic_id, message_id)

    def get_topic(self, name: str) -> GcpTopic:
        if name not in self.topics:
            topic_name = self.get_topic_name(name)
            self.topics[name] = self.factory.create_topic(topic_name)
        return self.topics[name]

    @classmethod
    def create(cls, factory: GcpAsyncFactory, config: BaseModel) -> Self:
        return cls(factory, config)

    @asynccontextmanager
    @abstractmethod
    async def manage_lifecycle(self, app: FastAPI):
        yield self

    def get_topic_name(self, task_name: str) -> str:
        if hasattr(self.config, f"{task_name}_topic"):
            return getattr(self.config, f"{task_name}_topic")
        else:
            raise ValueError(f"Topic for task '{task_name}' not found in config")
