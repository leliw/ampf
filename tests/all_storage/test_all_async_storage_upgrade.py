from typing import Type

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from ampf.base import BaseAsyncStorage, VersionedBaseModel
from ampf.gcp import GcpAsyncStorage
from ampf.in_memory import InMemoryAsyncStorage
from ampf.local import JsonMultiFilesAsyncStorage, JsonOneFileAsyncStorage


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    d_format_version_2: bool = False


config = AppConfig()


@pytest.fixture
def config_v2():
    config.d_format_version_2 = True
    yield
    config.d_format_version_2 = False


# There are two versions of stored data
class D_v1(BaseModel):
    name: str
    value1: str


class D_v2(VersionedBaseModel):
    v: int = 2
    name: str
    value2: str
    value3: str = ""

    @classmethod
    def from_storage(cls, data: dict):
        try:
            return cls.model_validate(data)
        except ValidationError:
            v1 = D_v1.model_validate(data)
            return cls(name=v1.name, value2=v1.value1)

    def to_storage(self):
        if config.d_format_version_2:
            return self.model_dump(by_alias=True, exclude_none=True)
        else:
            return D_v1(name=self.name, value1=self.value2).model_dump(by_alias=True, exclude_none=True)


@pytest.fixture(
    params=[
        InMemoryAsyncStorage,
        JsonOneFileAsyncStorage,
        JsonMultiFilesAsyncStorage,
        GcpAsyncStorage,
    ]
)
def clazz(gcp_factory, request) -> Type[BaseAsyncStorage]:
    return request.param


@pytest.fixture
async def storage_v1(clazz, tmp_path):
    if clazz in [JsonOneFileAsyncStorage, JsonMultiFilesAsyncStorage]:
        storage = clazz("tests-ampf-gcp", D_v1, key="name", root_path=tmp_path)  # type: ignore
    else:
        storage = clazz("tests-ampf-gcp", D_v1, key="name")
    yield storage
    await storage.drop()


@pytest.fixture
async def storage_v2(clazz, tmp_path):
    if clazz in [JsonOneFileAsyncStorage, JsonMultiFilesAsyncStorage]:
        storage = clazz("tests-ampf-gcp", D_v2, key="name", root_path=tmp_path)  # type: ignore
    else:
        storage = clazz("tests-ampf-gcp", D_v2, key="name")
    yield storage
    await storage.drop()


def test_v1_to_v2():
    # Given: An v1 object
    v1 = D_v1(name="test", value1="value1")
    # When: Convert to v2
    v2 = D_v2.from_storage(v1.model_dump(by_alias=True, exclude_none=True))
    # Then: It is converted
    assert v2.v == 2
    assert v2.name == "test"
    assert v2.value2 == "value1"


def test_v2_to_v1():
    # Given: An v2 object
    v2 = D_v2(name="test", value2="value2")
    # When: Convert to v1
    v1 = D_v1.model_validate(v2.to_storage())
    # Then: It is converted
    assert v1.name == "test"
    assert v1.value1 == "value2"


def test_v2_to_v2(config_v2):
    # Given: An v2 object
    v2 = D_v2(name="test", value2="value2")
    # And: v2 is set
    assert config.d_format_version_2
    # When: Convert to dict
    d = v2.to_storage()
    # Then: Dict is in version 2
    assert d["name"] == "test"
    assert d["value2"] == "value2"


@pytest.mark.asyncio
async def test_read_v1(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2]):
    # Given: A stored v1 object
    await storage_v1.create(D_v1(name="test", value1="value"))
    # When: It is read in v2 format
    d = await storage_v2.get("test")
    # Then: It is v2
    assert d.v == 2
    assert d.name == "test"
    assert d.value2 == "value"


@pytest.mark.asyncio
async def test_write_v2_to_v1(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2]):
    # Given: A given v2 object
    v2 = D_v2(name="test", value2="value", value3="value3")
    # When: Store in v1 format
    await storage_v2.create(v2)
    # Then: It can be read by v1 storage
    d = await storage_v1.get("test")
    # Then: It is v2
    assert d.name == "test"
    assert d.value1 == "value"


@pytest.mark.asyncio
async def test_write_v2_to_v2(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2], config_v2):
    # Given: A given v2 object
    v2 = D_v2(name="test", value2="value", value3="value3")
    # When: Store in v1 format
    await storage_v2.create(v2)
    # Then: It can be read by v1 storage
    d = await storage_v2.get("test")
    # Then: It is v2
    assert d.v == 2
    assert d.name == "test"
    assert d.value2 == "value"
    assert d.value3 == "value3"
