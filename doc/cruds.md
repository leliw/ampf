# CRUD Service

## `CRUDService`

```python
class CRUDService[R, H, C, U]:
    def __init__(
        self,
        storage: BaseAsyncCollectionStorage[R],
        record_class: type[R] | TypeAdapter[R],
        header_class: type[H],
        create_class: type[C] | None = None,
        update_class: type[U] | None = None,
    ) -> None:
        ...
```

The service parameters are:

* `storage` — asynchronous collection storage for records of type `R`;
* `record_class` — the record class or a `TypeAdapter` for the record type. A `TypeAdapter` can be used for discriminated unions;
* `header_class` — the header model class `H`;
* `create_class` — optional create model class `C`;
* `update_class` — optional update model class `U`.

A typed service can be created by subclassing `CRUDService`:

```python
class UserService(CRUDService[User, UserHeader, UserCreate, UserUpdate]):
    def __init__(
        self,
        storage: BaseAsyncCollectionStorage[User],
    ) -> None:
        super().__init__(
            storage,
            User,
            UserHeader,
            UserCreate,
            UserUpdate,
        )
```

## Methods

### `get_rows()`

Returns an asynchronous generator of header models.

```python
async for row in service.get_rows():
    print(row)
```

Each stored record is converted to the configured `header_class`.

### `create(value_create)`

Creates and stores a record. The argument can be:

* a create model (`C`), which is converted to a record when `create_class` is configured;
* an already-created record (`R`), which is validated using `record_class` or the configured `TypeAdapter`.

```python
user = await service.create(
    UserCreate(
        name="Alice",
        email="alice@example.com",
    )
)
```

The created record is returned.

### `get(record_id)`

Retrieves a record by its `UUID`.

```python
user = await service.get(user_id)
```

The underlying storage raises `KeyNotExistsException` if the record does not exist.

### `update(record_id, value_update)`

Applies a partial update using an update model.

Only fields explicitly set in the update model are modified. The `updated_at` field is always replaced with the current UTC timestamp.

```python
updated_user = await service.update(
    user_id,
    UserUpdate(name="Alice Smith"),
)
```

### `delete(record_id)`

Deletes a record by its `UUID`.

```python
await service.delete(user_id)
```

## Example models

```python
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str
    email: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class UserHeader(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
```

## Service configuration

```python
from ampf.cruds import CRUDService


class UserService(CRUDService[User, UserHeader, UserCreate, UserUpdate]):
    def __init__(
        self,
        storage: BaseAsyncCollectionStorage[User],
    ) -> None:
        super().__init__(
            storage,
            User,
            UserHeader,
            UserCreate,
            UserUpdate,
        )
```

The CRUD service is exported from `ampf.cruds`:

```python
from ampf.cruds import CRUDService
```
