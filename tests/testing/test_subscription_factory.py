import time
from uuid import uuid4

import pytest
from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from ampf.gcp import GcpTopic
from ampf.testing import SubscriptionFactory
from ampf.testing.api_test_client import ApiTestClient


class ServerConfig(BaseSettings):
    response_topic_name: str = "my-response-topic"


class D(BaseModel):
    name: str
    value: str


@pytest.fixture
def config() -> ServerConfig:
    config = ServerConfig()
    config.response_topic_name = "my-response-topic2-" + uuid4().hex
    return config


@pytest.fixture
def app(config: ServerConfig):
    app = FastAPI()

    @app.post("/pub-sub/push")
    async def pub_sub_push(d: D):
        GcpTopic(config.response_topic_name).publish(d)
        return d

    return app


@pytest.fixture
def client(app: FastAPI) -> ApiTestClient:  # type: ignore
    yield ApiTestClient(app)  # type: ignore


def test_subscription_factory(client: ApiTestClient, subscription_factory: SubscriptionFactory, config: ServerConfig):
    # Given: A subscription created by factory
    resp_sub = subscription_factory(config.response_topic_name, D)
    # And: A subscription emulator is run
    with resp_sub.run_push_emulator(client, "/pub-sub/push") as sub_emulator:
        # When: A message is published
        d = D(name="foo", value="bar")
        GcpTopic(config.response_topic_name).publish(d)
        # Then: It is received by the emulator
        while not sub_emulator.isfinished(timeout=120, expected_responses=1):
            time.sleep(0.1)
        # And: The payload is correct
        ret = sub_emulator.get_payloads()[0]
        assert ret == d
