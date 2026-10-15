# CRUDS

The `ampf.cruds` module provides generic asynchronous CRUD support for Pydantic models and collection storage.

```python
from ampf.cruds import CRUDRecord, CRUDService
```

## `CRUDRecord`

`CRUDRecord` is an abstract Pydantic model with common record fields:

* `id: UUID` — generated automatically.
* `created_at: datetime` — initialized with the current UTC time.
* `updated_at: datetime` — initialized with the current UTC time.

It uses four generic types:

* `H` — header/output model.
* `C` — create model.
* `P` — patch/update model.

Concrete records must implement:

```python
@classmethod
def create(cls, value_create: C) -> Self:
    ...

def to_header(self) -> H:
    ...
```

`create()` converts the create model into a record. `to_header()` converts a stored record into the model returned by `get_rows()`.

## `CRUDService`

```python
class CRUDService[T, H, C, P]:
    def __init__(
        self,
        storage: BaseAsyncCollectionStorage[T],
        clazz: type[T],
    ) -> None:
        ...
```

The service requires:

* `storage` — asynchronous collection storage for the record type.
* `clazz` — concrete `CRUDRecord` class.

A typed service can be created by subclassing:

```python
class UserService(CRUDService[User, UserHeader, UserCreate, UserPatch]):
    def __init__(self, storage: BaseAsyncCollectionStorage[User]) -> None:
        super().__init__(storage, User)
```

## Methods

### `get_rows()`

Returns an asynchronous generator of header models.

```python
async for row in service.get_rows():
    print(row)
```

Each stored record is converted using `to_header()`.

### `create(value_create)`

Creates and stores a record. The argument can be either:

* a create model (`C`), converted using `CRUDRecord.create()`;
* an already-created record (`T`), stored unchanged.

```python
user = await service.create(UserCreate(name="Alice"))
```

The created record is returned.

### `get(record_id)`

Retrieves a record by UUID.

```python
user = await service.get(user_id)
```

The underlying storage raises `KeyNotExistsException` when the record does not exist.

### `update(record_id, value_patch)`

Applies a partial update using a Pydantic patch model.

Only fields explicitly set in the patch model are updated. `updated_at` is always replaced with the current UTC timestamp.

```python
updated_user = await service.update(
    user_id,
    UserPatch(name="Alice Smith"),
)
```

### `delete(record_id)`

Deletes a record by UUID.

```python
await service.delete(user_id)
```

## Example model definitions

```python
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from ampf.cruds import CRUDRecord


class UserCreate(BaseModel):
    name: str
    email: str


class UserPatch(BaseModel):
    name: str | None = None
    email: str | None = None


class UserHeader(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime


class User(CRUDRecord[UserHeader, UserCreate, UserPatch]):
    name: str
    email: str

    @classmethod
    def create(cls, value_create: UserCreate) -> Self:
        return cls.model_validate(value_create.model_dump())

    def to_header(self) -> UserHeader:
        return UserHeader.model_validate(self.model_dump())
```

The CRUD components are exported from `ampf.cruds`:

```python
from ampf.cruds import CRUDRecord, CRUDService
```
