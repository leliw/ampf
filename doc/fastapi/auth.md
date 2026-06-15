# Authentication & Authorization

1. Backend - local authentication
    1. User management (CRUD)
    2. Authentication & authorization
    3. Password reset functionality
2. Frontend - authentication
    1. User authentication service
    2. User login form
    3. Password reset request form
    4. Password reset form
    5. Authentication interceptor
    6. Logout functionality
3. Frontend - authorization

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
from dependencies import UserServiceDep


router = APIRouter(tags=["Użytkownicy"])


@router.post("")
async def create(user_service: UserServiceDep, user: User):
    await user_service.create(user)


@router.get("")
async def get_all(user_service: UserServiceDep):
    return await user_service.get_all()


@router.get("/{username}")
async def get(user_service: UserServiceDep, username: str) -> User:
    return await user_service.get(username)


@router.put("/{username}")
async def update(user_service: UserServiceDep, username: str, user: User):
    return await user_service.update(username, user)


@router.delete("/{username}")
async def delete(user_service: UserServiceDep, username: str):
    return await user_service.delete(username)
```

Also add in `main.py`.

```python
app.include_router(users.router, prefix="/api/users")
```

### Config - DefaultUser

Add `default_user` property to `AppConfig`.

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

## 1.2 Authentication & authorization

### Roles

```python
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"


ROLE_DESCRIPTIONS = {
    Role.ADMIN: "Admin",
}
```

### Config - auth

```python
    auth: AuthConfig = AuthConfig(jwt_secret_key="")
```

### Dependencies - AuthServiceDep, AuthTokenDep, TokenPayloadDep, Authorize

```python
def get_auth_service(app_state: AppStateDep) -> AuthService:
    return AuthService(
        storage_factory=app_state.async_factory,
        user_service=app_state.user_service,
        auth_config=app_state.config.auth,
        email_sender_service=None,
        reset_mail_template=None,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


AuthTokenDep = Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="api/login"))]


async def decode_token(auth_service: AuthServiceDep, token: AuthTokenDep) -> TokenPayload:
    return await auth_service.decode_token(token)


TokenPayloadDep = Annotated[TokenPayload, Depends(decode_token)]


class Authorize:
    """Dependency for authorizing users based on their role."""

    def __init__(self, required_role: Role | None = None):
        self.required_role = required_role

    def __call__(self, token_payload: TokenPayloadDep) -> bool:
        if not self.required_role or self.required_role.value in token_payload.roles:
            return True
        else:
            raise InsufficientPermissionsError()
```

### Auth router

```python
from typing import Annotated, List

from ampf.auth import ChangePasswordData, Tokens
from core.roles import ROLE_DESCRIPTIONS, Role
from dependencies import AuthServiceDep, AuthTokenDep, TokenPayloadDep
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])

UserFormDataDep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/login")
async def login(auth_service: AuthServiceDep, form_data: UserFormDataDep) -> Tokens:
    return await auth_service.authorize(form_data.username, form_data.password)


@router.post("/logout")
async def logout(auth_service: AuthServiceDep, refresh_token: AuthTokenDep) -> None:
    await auth_service.add_to_black_list(refresh_token)


@router.post("/refresh-token")
async def refresh_token(auth_service: AuthServiceDep, refresh_token: AuthTokenDep) -> Tokens:
    return await auth_service.refresh_token(refresh_token)


@router.post("/change-password")
async def change_password(
    auth_service: AuthServiceDep,
    payload: ChangePasswordData,
    token_payload: TokenPayloadDep,
) -> None:
    await auth_service.change_password(token_payload.sub, payload.old_password, payload.new_password)


class RoleDto(BaseModel):
    name: str
    description: str


@router.get("/roles")
def get_roles() -> List[RoleDto]:
    return [RoleDto(name=role.value, description=ROLE_DESCRIPTIONS[role]) for role in Role]
```

```python
app.include_router(auth.router, prefix="/api")
```

### Add authentication & authorization checking

Add `Authorize` dependency to routers or endpoints:

- no `Authorize` dependency - available for all users
- `Authorize()` __without__ role - available for all authenticated users
- `Authorize(Role.ADMIN)` __with__ role - available for users with this role

```python
app.include_router(auth.router, prefix="/api")
app.include_router(config.router, prefix="/api/config")
app.include_router(users.router, prefix="/api/users", dependencies=[Depends(Authorize(Role.ADMIN))])
app.include_router(prompts.router, prefix="/api/prompts", dependencies=[Depends(Authorize())])
```

### Tests - auth

Modify & add fixtures:

```python
@pytest.fixture
def config(tmp_path) -> AppConfig:
    config = AppConfig(
        ...
        default_user=DefaultUser(username="test", email="test@test.com", password="test", roles=["admin"]),
        auth=AuthConfig(jwt_secret_key="test-test-test-test-test-test-test"),
    )
    return config


@pytest_asyncio.fixture
async def tokens(async_factory: BaseAsyncFactory, client: ApiTestClient) -> Tokens:
    # Clear token_black_list
    await async_factory.create_compact_storage("token_black_list", TokenExp, "token").drop()
    # Login
    return client.post_typed("/api/login", 200, Tokens, data={"username": "test", "password": "test"})


@pytest.fixture
def headers(tokens: Tokens) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens.access_token}"}
```

Remove empty `header()` fixture from `test_users.py` to use the above one.

#### tests\unit\routers\test_auth.py

```python
import time

from ampf.auth import Tokens
from routers.auth import RoleDto


def test_login_ok(client):
    # When: Default user logs in
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    r = response.json()
    # Then: The response contains access_token, refresh_token and token_type
    assert "access_token" in r
    assert "refresh_token" in r
    assert "token_type" in r
    assert r["token_type"] == "Bearer"


def test_login_wrong_password(client):
    # When: Default user logs in with wrong password
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "wrong"},
    )
    # Then: The response status code is 401
    assert response.status_code == 401


def test_login_wrong_username(client):
    # When: Default user logs in with wrong password
    response = client.post(
        "/api/login",
        data={"username": "admin@test", "password": "test"},
    )
    # Then: The response status code is 401
    assert response.status_code == 401


def test_logout(client, tokens: Tokens):
    # When: Default user logs out
    response = client.post(
        "/api/logout",
        headers={"Authorization": f"Bearer {tokens.refresh_token}"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200


def test_refresh_token(client, tokens: Tokens):
    # Wait for 1 second
    time.sleep(1)
    # When: Default user refreshes token
    response = client.post(
        "/api/refresh-token",
        headers={"Authorization": f"Bearer {tokens.refresh_token}"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    r = response.json()
    # Then: The response contains access_token, refresh_token and token_type
    assert "access_token" in r
    assert "refresh_token" in r
    assert "token_type" in r
    assert r["token_type"] == "Bearer"
    assert r["access_token"] != tokens.access_token
    assert r["refresh_token"] != tokens.refresh_token


def test_change_password(client, tokens: Tokens):
    # When: Default user changes password
    response = client.post(
        "/api/change-password",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
        json={"old_password": "test", "new_password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # When: Default user logs in with new password
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # Clean up
    assert (
        200
        == client.post(
            "/api/change-password",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            json={"old_password": "new_test", "new_password": "test"},
        ).status_code
    )


def test_get_roles(client):
    # When: Get roles
    roles = client.get_typed_list("/api/roles", 200, RoleDto)
    # Then: At least admin is returned
    assert len(roles) > 0
    assert "admin" in [role.name for role in roles]
```
