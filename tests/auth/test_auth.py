import re
import time

from tests.auth.app.features.user.user_model import User
from tests.auth.app.features.user.user_service import UserService


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
        data={"username": "test", "password": "new_test"},
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


def test_reset_password_request(email_sender, client, user_service: UserService):
    # Given: Stored an user with email 
    user_service.create(User(email="test@test.com", password="test"))
    # When: The user requests password reset
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


def test_reset_password(email_sender, client, user_service: UserService):
    # Given: Stored an user with email 
    user_service.create(User(email="test@test.com", password="test"))
    # Given: The user requests password reset
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
