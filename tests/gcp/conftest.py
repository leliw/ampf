import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import pytest

from ampf.gcp import GcpAsyncFactory, GcpTopic


class AppConfig(BaseSettings):
    project_id: str

    gcp_bucket_name: str
    gcp_database_1: str
    gcp_database_2: str
    gcp_topic_1: str
    gcp_topic_2: str

@pytest.fixture(scope="session")
def config():
    load_dotenv("./infra/env/it/.env.app")
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("./infra/env/it/.gcp_credentials.json")
    yield AppConfig()  # pyright: ignore[reportCallIssue]
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred

@pytest.fixture(scope="session")
def async_factory():
    return GcpAsyncFactory()


@pytest.fixture(scope="session")
def existing_topic():
    topic = GcpTopic(topic_id="ampf_unit_tests_existing_topic")
    topic.create(exist_ok=True)
    yield topic
    topic.delete()


@pytest.fixture(scope="session")
def existing_subscription(existing_topic: GcpTopic):
    subscription = existing_topic.create_subscription(exist_ok=True)
    yield subscription
    subscription.delete()


@pytest.fixture(scope="session")
def topic(config: AppConfig):
    topic = GcpTopic(config.gcp_topic_1, project_id=config.project_id)
    return topic


@pytest.fixture(scope="session")
def subscription(topic: GcpTopic):
    subscription = topic.create_subscription(exist_ok=True)
    return subscription


@pytest.fixture(scope="session")
def topic2(config: AppConfig):
    topic = GcpTopic(config.gcp_topic_2, project_id=config.project_id)
    return topic


@pytest.fixture(scope="session")
def subscription2(topic2: GcpTopic):
    subscription = topic2.create_subscription(exist_ok=True)
    return subscription
