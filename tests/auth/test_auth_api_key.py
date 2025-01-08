from fastapi.testclient import TestClient
import pytest

from ampf.auth.auth_model import APIKey, APIKeyRequest, APIKeyInDB
from ampf.base import BaseFactory, BaseStorage, KeyNotExistsException
from tests.auth.app.features.user.user_service import UserService


@pytest.fixture
def api_key_storage(factory: BaseFactory) -> BaseStorage[APIKeyInDB]:
    return factory.create_compact_storage("api_keys", APIKeyInDB, "key_hash")


def test_generate(
    client: TestClient, auth_header, api_key_storage: BaseStorage[APIKeyInDB]
):
    # Given: ApiKeyRequest
    req = APIKeyRequest()
    # When: API key is generated
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=req.model_dump(),
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # And: API key is returned
    assert "key" in response.json()
    assert "username" in response.json()
    assert "exp" in response.json()
    assert "roles" in response.json()
    # And: API key is stored
    r = APIKey(**response.json())
    stored = api_key_storage.get(response.json()["key_hash"])
    assert stored.username == r.username
    assert stored.exp == r.exp
    assert stored.roles == r.roles
    assert "key" not in stored.model_dump()
    api_key_storage.drop()


def test_authorize_ok(
    client: TestClient, auth_header, api_key_storage: BaseStorage[APIKeyInDB]
):
    # Given: A generated API key
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=APIKeyRequest().model_dump(),
    )
    key = response.json()["key"]
    # When: Get users with the key
    response = client.get("/api/users", headers={"Authorization": f"Bearer {key}"})
    # Then: The response status code is 200
    assert response.status_code == 200
    assert 1 == len(response.json())
    api_key_storage.drop()

def test_authorize_disabled_user(
    client: TestClient, auth_header, api_key_storage: BaseStorage[APIKeyInDB], user_service: UserService
):
    # Given: A generated API key
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=APIKeyRequest().model_dump(),
    )
    key = response.json()["key"]
    # And: User is disabled
    user = user_service.get("test")
    user.disabled = True
    user_service.update(user.username, user)
    # When: Get users with the key
    response = client.get("/api/users", headers={"Authorization": f"Bearer {key}"})
    # Then: The response status code is 401
    assert response.status_code == 401
    api_key_storage.drop()



def test_get_user_api_keys(
    client: TestClient, auth_header, api_key_storage: BaseStorage[APIKeyInDB]
):
    # Given: A generated API key
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=APIKeyRequest().model_dump(),
    )
    key_hash = response.json()["key_hash"]
    # When: Get all keys for current user
    response = client.get("/api/api-keys", headers=auth_header)
    # Then: The response status code is 200
    assert response.status_code == 200
    assert 1 == len(response.json())
    assert key_hash == response.json()[0]["key_hash"]
    # Clean up
    api_key_storage.drop()


def test_delete_api_key_ok(
    client: TestClient, auth_header, api_key_storage: BaseStorage[APIKeyInDB]
):
    # Given: A generated API key
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=APIKeyRequest().model_dump(),
    )
    key_hash = response.json()["key_hash"]
    # When: Delete the key
    response = client.delete(
        f"/api/api-keys/{key_hash}",
        headers=auth_header,
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # And: Key is deleted from storage
    with pytest.raises(KeyNotExistsException):
        api_key_storage.get(key_hash)


def test_delete_api_key_wrong_user(
    client: TestClient, auth_header, auth_header2, api_key_storage: BaseStorage[APIKeyInDB],
):
    # Given: A generated API key by first user
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=APIKeyRequest().model_dump(),
    )
    key_hash = response.json()["key_hash"]
    # When: Delete the key by secod user
    response = client.delete(
        f"/api/api-keys/{key_hash}",
        headers=auth_header2,
    )
    # Then: The response status code is 200
    assert response.status_code == 404
    # And: Key still exists
    st_key = api_key_storage.get(key_hash)
    assert st_key.username == "test"



