import re
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from ampf.auth.auth_model import TokenExp
from ampf.in_memory.in_memory_factory import InMemoryFactory
from tests.auth.app.config import DefaultUserConfig, ServerConfig
from tests.auth.app.dependencies import get_email_sender, get_factory, get_server_config
from tests.auth.app.features.user.user_service import UserService
from tests.auth.app.routers import auth, users


@pytest.fixture
def test_server_config(tmp_path: str) -> ServerConfig:
    return ServerConfig(
        data_dir=str(tmp_path),
        default_user=DefaultUserConfig(
            email="test@test.com", password="test", roles=["admin"]
        ),
    )


@pytest.fixture
def client(factory, email_sender, test_server_config: ServerConfig) -> TestClient:
    UserService(InMemoryFactory()).initialize_storege_with_user(
        test_server_config.default_user
    )

    app = FastAPI()
    app.dependency_overrides[get_factory] = lambda: factory
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    app.dependency_overrides[get_server_config] = lambda: test_server_config

    app.include_router(prefix="/api", router=auth.router)
    app.include_router(prefix="/api/users", router=users.router)

    client = TestClient(app)
    return client


def test_login_ok(client):
    # When: Default user logs in
    response = client.post(
        "/api/login",
        data={"username": "test@test.com", "password": "test"},
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
        data={"username": "test@test.com", "password": "wrong"},
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


@pytest.fixture
def tokens(factory, client):
    # Clear token_black_list
    factory.create_compact_storage("token_black_list", TokenExp, "token").drop()
    # Login
    response = client.post(
        "/api/login",
        data={"username": "test@test.com", "password": "test"},
    )
    r = response.json()
    return r


def test_logout(client, tokens):
    # When: Default user logs out
    response = client.post(
        "/api/logout",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200


def test_refresh_token(client, tokens):
    # Wait for 1 second
    time.sleep(1)
    # When: Default user refreshes token
    response = client.post(
        "/api/token-refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    r = response.json()
    # Then: The response contains access_token, refresh_token and token_type
    assert "access_token" in r
    assert "refresh_token" in r
    assert "token_type" in r
    assert r["token_type"] == "Bearer"
    assert r["access_token"] != tokens["access_token"]
    assert r["refresh_token"] != tokens["refresh_token"]

def test_change_password(client, tokens):
    # When: Default user changes password
    response = client.post(
        "/api/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"old_password": "test", "new_password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # When: Default user logs in with new password
    response = client.post( 
        "/api/login",
        data={"username": "test@test.com", "password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # Clean up
    assert (
        200
        == client.post(
            "/api/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"old_password": "new_test", "new_password": "test"},
        ).status_code
    )


def test_reset_password_request(email_sender, client):
    # When: Default user requests password reset
    response = client.post(
        "/api/reset-password-request",
        json={"email": "test@test.com"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # Then: Email was sent
    assert len(email_sender.sent_emails) == 1
    email = email_sender.sent_emails[0]
    assert email["recipient"] == "test@test.com"
    match = re.search(r"wpisz kod: (\S+) w formularzu\.", email["body"])
    code = match.group(1)
    assert len(code) == 16
    match = re.search(r"Kod jest ważny przez (\d+) minut\.", email["body"])
    time = match.group(1)
    assert time == "15"


def test_reset_password(email_sender, client):
    # Given: Default user requests password reset
    client.post(
        "/api/reset-password-request",
        json={"email": "test@test.com"},
    )
    # Given: Code is extracted from email
    assert len(email_sender.sent_emails) == 1
    email = email_sender.sent_emails[0]
    match = re.search(r"wpisz kod: (\S+) w formularzu\.", email["body"])
    code = match.group(1)
    # When: Default user resets password with the code
    response = client.post(
        "/api/reset-password",
        json={"email": "test@test.com", "reset_code": code, "new_password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # Then: Default user logs in with new password
    response = client.post(
        "/api/login",
        data={"username": "test@test.com", "password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
