# Authentication & Authorization

1. Backend - local authentication
    1. User management (CRUD)
    2. Authentication system
    3. Password reset functionality
2. Backend - authorization
3. Frontend - authentication
    1. User authentication service
    2. User login form
    3. Password reset request form
    4. Password reset form
    5. Authentication interceptor
    6. Logout functionality
4. Frontend - authorization

## 1.1 Backend - User management (CRUD)

### User model

Simplest classes.

```python
from typing import Any

from pydantic import model_serializer

from ampf.auth.auth_model import AuthUser


class UserHeader(AuthUser):
    pass


class User(UserHeader):
    pass


class UserInDB(User):
    @model_serializer
    def ser_model(self) -> dict[str, Any]:
        ret = dict(self)
        ret.pop("password", None)
        return ret
```

### User service

```python
from pydantic import EmailStr

from ampf.base import BaseAsyncFactory, KeyNotExistsException

from ampf.auth import BaseUserService
from .user_model import User, UserHeader, UserInDB


class UserService(BaseUserService[User]):
    """User service implementation"""

    def __init__(self, factory: BaseAsyncFactory) -> None:
        super().__init__(User)
        self.storage = factory.create_compact_storage("users", UserInDB, "username")

    async def get_user_by_email(self, email: EmailStr) -> User:
        async for user in self.storage.where("email", "==", email).get_all():
            return user
        raise KeyNotExistsException(email)

    async def get_all(self) -> list[UserHeader]:
        return [UserHeader(**i.model_dump(by_alias=True)) async for i in self.storage.get_all()]

    async def get(self, key: str) -> User:
        return await self.storage.get(key)

    async def put(self, key: str, user: User) -> None:
        user_in_db = UserInDB(**dict(user))
        await self.storage.put(key, user_in_db)

    async def delete(self, key: str) -> None:
        await self.storage.delete(key)

    async def is_empty(self) -> bool:
        return await self.storage.is_empty()
```

### Users router

```python
from fastapi import APIRouter

from core.users.user_model import User
from dependencies import UserServceDep


router = APIRouter(tags=["Użytkownicy"])


@router.post("")
async def create(user_service: UserServceDep, user: User):
    await user_service.create(user)


@router.get("")
async def get_all(user_service: UserServceDep):
    return await user_service.get_all()


@router.get("/{username}")
async def get(user_service: UserServceDep, username: str) -> User:
    return await user_service.get(username)


@router.put("/{username}")
async def update(user_service: UserServceDep, username: str, user: User):
    return await user_service.update(username, user)


@router.delete("/{username}")
async def delete(user_service: UserServceDep, username: str):
    return await user_service.delete(username)
```

Also add in `main.py`.

```python
app.include_router(users.router, prefix="/api/users")
```

### Config - DefaultUser

Add `defualt_user` property to `AppConfig`.

```python
    default_user: DefaultUser = DefaultUser(username="admin", password="")
```

### Dependency - UserServiceDep

```python
async def user_service_dep(app_config: AppConfigDep, factory: AsyncFactoryDep) -> UserService:
    service = UserService(factory)
    await service.initialise_storage(app_config.default_user)
    return service


UserServiceDep = Annotated[UserService, Depends(user_service_dep)]
```

### Tests - Users

The headers fixture will be changed later.

```python
import pytest

from core.users.user_model import User, UserHeader
from ampf.testing import ApiTestClient

@pytest.fixture
def headers() -> dict[str, str]:
    return {}


def test_get_all(client: ApiTestClient, headers):
    # Given: An initialized storage with default user
    # When: I get all users
    r = client.get_typed_list("/api/users", 200, UserHeader, headers=headers)
    # Then: I get only default user
    assert 1 == len(r)


def test_post_get_put_delete(client: ApiTestClient, headers):
    # POST
    user = User(username="mr.bean@gmail.com", email="mr.bean@gmail.com")
    client.post("/api/users", 200, json=user, headers=headers)

    # GET
    r = client.get_typed(f"/api/users/{user.username}", 200, User, headers=headers)
    assert user.username == r.username

    # PUT
    user.email = "mr.bean2@gmail.com"
    r = client.put(f"/api/users/{user.username}", 200, json=user, headers=headers)
    r = client.get_typed(f"/api/users/{user.username}", 200, User, headers=headers)
    assert user.email == r.email

    # DELETE
    client.delete(f"/api/users/{user.username}", 200, headers=headers)
    client.get(f"/api/users/{user.username}", 404, headers=headers)
```
