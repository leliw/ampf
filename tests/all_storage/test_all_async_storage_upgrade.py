import logging
from typing import Any, Type

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from ampf.base import BaseAsyncStorage, VersionedBaseModel
from ampf.base.versioned_base_model import StorageFormatFlags
from ampf.gcp import GcpAsyncStorage
from ampf.in_memory import InMemoryAsyncStorage
from ampf.local import JsonMultiFilesAsyncStorage, JsonOneFileAsyncStorage

_log = logging.getLogger(__name__)


class FeatureFlags(BaseModel):
    d_v2_storage: bool = False
    d_v2_migrate: bool = False

    def model_post_init(self, _) -> None:
        for k, v in self.model_dump().items():
            _log.info("Feature flag: %s = %s", k, v)


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    feature_flags: FeatureFlags = FeatureFlags()


config = AppConfig()


# There are two versions of stored data
class D_v1(BaseModel):
    name: str
    value1: str


class D_v2(VersionedBaseModel):
    CURRENT_VERSION = 2
    name: str
    value2: str
    value3: str = ""

    @classmethod
    def from_storage(cls, data: dict):
        try:
            return cls.model_validate(data)
        except ValidationError:
            v1 = D_v1.model_validate(data)
            return cls(v=1, name=v1.name, value2=v1.value1)

    def to_storage(self):
        if self.FORMAT_FLAGS.save_new_format:
            return self.model_dump(by_alias=True, exclude_none=True)
        else:
            return D_v1(name=self.name, value1=self.value2).model_dump(by_alias=True, exclude_none=True)

D = D_v2

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


@pytest.fixture
def config_v2():
    config.feature_flags.d_v2_storage = True
    D_v2.FORMAT_FLAGS = StorageFormatFlags(
        save_new_format=config.feature_flags.d_v2_storage,
        migrate_legacy_on_read=config.feature_flags.d_v2_migrate,
    )
    yield
    config.feature_flags.d_v2_storage = False
    D_v2.FORMAT_FLAGS = StorageFormatFlags(
        save_new_format=config.feature_flags.d_v2_storage,
        migrate_legacy_on_read=config.feature_flags.d_v2_migrate,
    )

@pytest.fixture
def config_v3():
    config.feature_flags.d_v2_storage = True
    config.feature_flags.d_v2_migrate = True
    D_v2.FORMAT_FLAGS = StorageFormatFlags(
        save_new_format=config.feature_flags.d_v2_storage,
        migrate_legacy_on_read=config.feature_flags.d_v2_migrate,
    )
    yield
    config.feature_flags.d_v2_storage = False
    D_v2.FORMAT_FLAGS = StorageFormatFlags(
        save_new_format=config.feature_flags.d_v2_storage,
        migrate_legacy_on_read=config.feature_flags.d_v2_migrate,
    )

def test_v1_to_v2():
    # Given: An v1 object
    v1 = D_v1(name="test", value1="value1")
    # When: Convert to v2
    v2 = D_v2.from_storage(v1.model_dump(by_alias=True, exclude_none=True))
    # Then: It is converted
    assert v2.CURRENT_VERSION == 2
    assert v2.name == "test"
    assert v2.value2 == "value1"
    # And: It is stored in v1
    assert v2.v == 1



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
    assert config.feature_flags.d_v2_storage
    # When: Convert to dict
    d = v2.to_storage()
    # Then: Dict is in version 2
    assert d["name"] == "test"
    assert d["value2"] == "value2"


@pytest.mark.asyncio
async def test_write_v1_to_v1(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2]):
    # Given: A stored v1 object
    await storage_v1.create(D_v1(name="test", value1="value"))
    # When: It is read in v2 format
    d = await storage_v2.get("test")
    # Then: It is v2
    assert d.name == "test"
    assert d.value2 == "value"
    # And: It is stored in v1
    assert d.v == 1



@pytest.mark.asyncio
async def test_write_v2_to_v1(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2]):
    # Given: A given v2 object
    v2 = D_v2(name="test", value2="value", value3="value3")
    # When: Store in v1 format
    await storage_v2.create(v2)
    # Then: It can be read by v1 storage
    d = await storage_v1.get("test")
    # Then: It is v1
    assert d.name == "test"
    assert d.value1 == "value"
    # And: It is stored in v1
    assert "v" not in d.model_dump().keys()



@pytest.mark.asyncio
async def test_write_v2_to_v2(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2], config_v2):
    # Given: A given v2 object
    v2 = D_v2(name="test", value2="value", value3="value3")
    # When: Store in v1 format
    await storage_v2.create(v2)
    # Then: It can be read by v2 storage
    d = await storage_v2.get("test")
    # Then: It is v2
    assert d.CURRENT_VERSION == 2
    assert d.name == "test"
    assert d.value2 == "value"
    assert d.value3 == "value3"
    # And: It is stored in v2
    assert d.v == 2


@pytest.mark.asyncio
async def test_migrate_v1_to_v2(storage_v1: BaseAsyncStorage[D_v1], storage_v2: BaseAsyncStorage[D_v2], config_v3):
    # Given: A stored v1 object
    await storage_v1.create(D_v1(name="test", value1="value"))
    # When: It is read in v2 format
    d = await storage_v2.get("test")
    # Then: It is v2
    assert d.CURRENT_VERSION == 2
    assert d.name == "test"
    assert d.value2 == "value"
    # And: It is stored in v2
    assert d.v == 2
    
