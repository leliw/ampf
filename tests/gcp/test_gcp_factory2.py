import os
from uuid import UUID, uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import pytest

from ampf.gcp import GcpFactory


class AppConfig(BaseSettings):
    project_id: str

    gcp_bucket_name: str
    gcp_database_1: str
    gcp_database_2: str


class D(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    name: str


@pytest.fixture
def config():
    load_dotenv("./infra/env/it/.env.app")
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("./infra/env/it/.gcp_credentials.json")
    yield AppConfig()  # pyright: ignore[reportCallIssue]
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred


def test_two_databases(config: AppConfig):
    # Given: Two factories
    factory1 = GcpFactory(database=config.gcp_database_1, project_id=config.project_id)
    factory2 = GcpFactory(database=config.gcp_database_2, project_id=config.project_id)
    # And: Two storages
    storage1 = factory1.create_storage("test", D)
    storage2 = factory2.create_storage("test", D)
    # When: Two records are created in different storages
    rec1 = D(name="t1")
    rec2 = D(name="t2")
    storage1.create(rec1)
    storage2.create(rec2)
    # Then: The storages are separated
    assert storage1.key_exists(rec1.uuid)
    assert not storage2.key_exists(rec1.uuid)
    assert storage2.key_exists(rec2.uuid)
    assert not storage1.key_exists(rec2.uuid)
    # CleanUp:
    storage1.drop()
    storage2.drop()
