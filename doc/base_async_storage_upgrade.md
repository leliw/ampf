# BaseAsyncStorage (upgrade)

## How to

### Step 1

In step 1 the appliaction uses a new data format but always store data in old format, both data format versions can be read from storage.
The application can be reverted to the previous version handling only old data format.

1. Rename current version (without number) to `_v1` and add `v: int = 1` property
2. Create new version (`_v2`) inherited from `VersionBaseModel`
3. Define current version as `_v2`
   - set `CURRENT_VERSION = 2` class property
   - add `from_storage` and `to_storage` methods
4. Define **feature flags** class and setting these flags (i.e. from app_config)
5. 

### Step 2

Data are stored only in new version format. It can be done by feature flag

### Step 3

All data read in old version are immediately stored in new vesion format. It can be done by feature flag.

### Step 4

A job converts all data in old format into new format.

### Step 5

All old version's related code is removed from source code.

## StorageFormatFlags

A class used by `VersionedBaseModel` to define storage format version.

```python
class StorageFormatFlags(BaseModel):
    """Flags for storage format."""
    save_new_format: bool = Field(default=False)
    """Whether to save data in the new format. If false, the old format will be used for saving data."""
    migrate_legacy_on_read: bool = Field(default=False)
    """Whether to migrate legacy data on read. If true, legacy data will be migrated to the new format."""
```

Flags are usually set by application config.

```python
class FeatureFlags(BaseModel):
    d_v2_storage: bool = False
    d_v2_migrate: bool = False

    def model_post_init(self, _) -> None:
        for k, v in self.model_dump().items():
            _log.info("Feature flag: %s = %s", k, v)

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    feature_flags: FeatureFlags = FeatureFlags()
```

And then class properties are set in `dependecy.py`.

```python
def lifespan(config: AppConfig):
    _log.info("Version: %s", config.version)
    app_state = AppState.create(config)
    D_v2.FORMAT_FLAGS = StorageFormatFlags(
        save_new_format=config.feature_flags.d_v2_storage,
        migrate_legacy_on_read=config.feature_flags.d_v2_migrate,
    )
...
```

## VersionedBaseModel

A class inheriting from BaseModel dedicated to versioning data stored in the (async) storage.

```python
class VersionedBaseModel(BaseModel, ABC):
    CURRENT_VERSION: ClassVar[int] = 1  # Override in subclasses
    FORMAT_FLAGS: ClassVar[StorageFormatFlags] = StorageFormatFlags()

    v: int = Field(..., ge=1, description="Schema version from storage")

    @classmethod
    @abstractmethod
    def from_storage(cls, data: Dict[str, Any]):
        """Convert the data from storage format to the model instance.

        Args:
            data: The data to convert.
        Returns:
            The converted data.
        """
        return cls.model_validate(data)

    @abstractmethod
    def to_storage(self) -> Dict[str, Any]:
        """Convert the data to storage format.

        Returns:
            The converted data.
        """
        return self.model_dump(by_alias=True, exclude_none=True)
```

These two methods should be used to convert between versions. "v" property is designed to store version number.

```python
# There are two versions of stored data
class D_v1(BaseModel):
    v: int = 1
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
            return cls(v=v1.v, name=v1.name, value2=v1.value1)

    def to_storage(self):
        if self.FORMAT_FLAGS.save_new_format:
            return self.model_dump(by_alias=True, exclude_none=True)
        else:
            return D_v1(name=self.name, value1=self.value2).model_dump(by_alias=True, exclude_none=True)
```

Method `from_storage()` has to read all (previous) versions and convers them to current version.
Method `to_storage()` returns current or previous version - always the same. In the example above, the
version saved depends on the configuration.

## BaseAsyncStorage

BaseAsyncStorage class has also methods `from_storage()` and `to_storage()`. By default they use methods from `VersionedBaseModel`,
but in storage they can be extended, more complex and also asynchronous.

```python
    def to_storage(self, data: T) -> Dict[str, Any] | Coroutine[Any, Any, Dict[str, Any]]:
        if isinstance(data, VersionedBaseModel):
            return data.to_storage()
        else:
            return data.model_dump(by_alias=True, exclude_none=True)

    def from_storage(self, data: Dict[str, Any]) -> T | Coroutine[Any, Any, T]:
        if issubclass(self.clazz, VersionedBaseModel):
            ret = self.clazz.from_storage(data)
            if ret.FORMAT_FLAGS.migrate_legacy_on_read and ret.CURRENT_VERSION != ret.v:
                async def save_and_return():
                    ret.v = ret.CURRENT_VERSION
                    await self.save(ret)
                    return ret
                return save_and_return()
            else:
                return ret
        else:
            return self.clazz.model_validate(data)
```