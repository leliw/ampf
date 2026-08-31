import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Self

from fastapi import FastAPI
from pydantic import BaseModel

from ampf.gcp import GcpAsyncFactory
from ampf.gcp.gcp_topic import GcpTopic
from ampf.tasks.task_registry import TaskRegistry

from .task_model import ManagedTaskRunner

_log = logging.getLogger(__name__)


class PubsubRunner(ManagedTaskRunner, ABC):
    def __init__(self, factory: GcpAsyncFactory, config: BaseModel):
        self.factory = factory
        self.config = config
        self._initialized = False
        self.topics: dict[str, GcpTopic] = {}

    def run(self, name: str, payload: BaseModel):
        definition = self.get_definition(name)
        topic = self.get_topic(name, definition.external)
        response_topic_name = self.get_response_topic_name(name) if definition.external else None
        message_id = topic.publish(payload, response_topic=response_topic_name)
        _log.info("Published message in topic %s with ID: %s", topic.topic_id, message_id)

    async def run_async(self, name: str, payload: BaseModel):
        definition = self.get_definition(name)
        topic = self.get_topic(name, definition.external)
        response_topic_name = self.get_response_topic_name(name) if definition.external else None
        message_id = await topic.publish_async(payload, response_topic=response_topic_name)
        _log.info("Published message in topic %s with ID: %s", topic.topic_id, message_id)

    def get_topic(self, name: str, external: bool = False) -> GcpTopic:
        if name not in self.topics:
            topic_name = self.get_topic_name(name, external)
            self.topics[name] = self.factory.create_topic(topic_name)
        return self.topics[name]

    @classmethod
    def create(cls, factory: GcpAsyncFactory, config: BaseModel | Any) -> Self:
        return cls(factory, config)

    @asynccontextmanager
    @abstractmethod
    async def manage_lifecycle(self, app: FastAPI):
        yield self

    def get_topic_name(self, task_name: str, external: bool = False) -> str:
        property_name = f"{task_name}_request_topic" if external else f"{task_name}_topic"
        if hasattr(self.config, property_name):
            return getattr(self.config, property_name)
        else:
            raise ValueError(f"Topic for task '{task_name}' not found in config ({property_name}).")

    def get_definition(self, task_name: str):
        try:
            return TaskRegistry._tasks[task_name]
        except KeyError:
            raise ValueError(f"Task '{task_name}' is not registered in TaskRegistry")

    def get_response_topic_name(self, task_name: str) -> str:
        property_name = f"{task_name}_response_topic"
        if hasattr(self.config, property_name):
            return getattr(self.config, property_name)
        else:
            raise ValueError(f"Response topic for task '{task_name}' not found in config ({property_name}).")
