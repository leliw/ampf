import pytest

from ampf.auth.auth_config import DefaultUser


def test_default_user_username_is_not_email():
    user = DefaultUser(username="admin", password="admin")
    assert user.username == "admin"
    assert user.email is None


def test_default_user_username_is_email():
    user = DefaultUser(username="admin@google.com", password="admin")
    assert user.username == "admin@google.com"
    assert user.email == "admin@google.com"


def test_default_user_email_not_username():
    user = DefaultUser(email="admin@example.com", password="admin")
    assert user.username == "admin@example.com"
    assert user.email == "admin@example.com"


def test_default_user_username_and_email():
    user = DefaultUser(username="admin", email="admin@google.com", password="admin")
    assert user.username == "admin"
    assert user.email == "admin@google.com"


def test_default_user_error():
    with pytest.raises(ValueError):
        DefaultUser(password="admin")
