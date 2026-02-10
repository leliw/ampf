from typing import Dict, Iterator
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest
import pytest_asyncio

from ampf.auth import TokenExp, DefaultUser, AuthConfig
from ampf.base import BaseAsyncFactory
from ampf.base.exceptions import KeyNotExistsException

from ampf.in_memory.in_memory_async_factory import InMemoryAsyncFactory
from tests.auth.app.config import ServerConfig
from tests.auth.app.dependencies import get_async_factory, get_email_sender, get_server_config
from tests.auth.app.features.user.user_model import User
from tests.auth.app.features.user.user_service import UserService
from tests.auth.app.routers import auth, users


@pytest.fixture
def factory() -> BaseAsyncFactory:
    """Return an instance of the in-memory factory."""
    return InMemoryAsyncFactory()


@pytest.fixture
def test_user() -> DefaultUser:
    return DefaultUser(username="test", password="test", roles=["admin"])


@pytest.fixture
def test_server_config(tmp_path: str, test_user) -> ServerConfig:
    return ServerConfig(
        data_dir=str(tmp_path),
        default_user=test_user,
        auth=AuthConfig(jwt_secret_key="asdasdasd"),
    )


@pytest_asyncio.fixture
async def user_service(factory, test_server_config: ServerConfig) -> UserService: # type: ignore
    ret = UserService(factory)
    await ret.initialise_storage(test_server_config.default_user)
    yield ret # type: ignore
    await ret.storage.drop()


@pytest.fixture
def client(
    factory, email_sender, test_server_config: ServerConfig, user_service: UserService
) -> Iterator[TestClient]:

    app = FastAPI()
    app.dependency_overrides[get_async_factory] = lambda: factory
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    app.dependency_overrides[get_server_config] = lambda: test_server_config

    app.include_router(prefix="/api", router=auth.router)
    app.include_router(prefix="/api/users", router=users.router)

    app.add_exception_handler(
        KeyNotExistsException,
        lambda request, exc: JSONResponse({"detail": str(exc)}, status_code=404),
    )
    client = TestClient(app)
    yield client


@pytest_asyncio.fixture
async def tokens(factory: BaseAsyncFactory, client: TestClient):
    # Clear token_black_list
    await factory.create_compact_storage("token_black_list", TokenExp, "token").drop()
    # Login
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "test"},
    )
    r = response.json()
    return r


@pytest.fixture
def auth_header(tokens) -> Dict[str, str]:
    return {"Authorization": f"Bearer {tokens["access_token"]}"}


@pytest_asyncio.fixture
async def auth_header2(user_service: UserService, client: TestClient) -> Dict[str, str]:
    await user_service.create(User(email="test2@test.com", password="test2", roles=["admin"]))
    # Login
    response = client.post(
        "/api/login",
        data={"username": "test2@test.com", "password": "test2"},
    )
    r = response.json()
    return {"Authorization": f"Bearer {r["access_token"]}"}
