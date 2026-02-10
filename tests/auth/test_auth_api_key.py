import pytest
from fastapi.testclient import TestClient

from ampf.auth.auth_model import APIKey, APIKeyInDB, APIKeyRequest
from ampf.base import BaseAsyncFactory, BaseAsyncStorage, KeyNotExistsException
from tests.auth.app.features.user.user_service import UserService


@pytest.fixture
def api_key_storage(factory: BaseAsyncFactory) -> BaseAsyncStorage[APIKeyInDB]:
    return factory.create_compact_storage("api_keys", APIKeyInDB, "key_hash")


@pytest.mark.asyncio
async def test_generate(client: TestClient, auth_header, api_key_storage: BaseAsyncStorage[APIKeyInDB]):
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
    stored = await api_key_storage.get(response.json()["key_hash"])
    assert stored.username == r.username
    assert stored.exp == r.exp
    assert stored.roles == r.roles
    assert "key" not in stored.model_dump()
    await api_key_storage.drop()


@pytest.mark.asyncio
async def test_authorize_ok(client: TestClient, auth_header, api_key_storage: BaseAsyncStorage[APIKeyInDB]):
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
    await api_key_storage.drop()


@pytest.mark.asyncio
async def test_authorize_disabled_user(
    client: TestClient, auth_header, api_key_storage: BaseAsyncStorage[APIKeyInDB], user_service: UserService
):
    # Given: A generated API key
    response = client.post(
        "/api/api-keys",
        headers=auth_header,
        json=APIKeyRequest().model_dump(),
    )
    key = response.json()["key"]
    # And: User is disabled
    user = await user_service.get("test")
    user.disabled = True
    await user_service.update(user.username, user)
    # When: Get users with the key
    response = client.get("/api/users", headers={"Authorization": f"Bearer {key}"})
    # Then: The response status code is 401
    assert response.status_code == 401
    await api_key_storage.drop()


@pytest.mark.asyncio
async def test_get_user_api_keys(client: TestClient, auth_header, api_key_storage: BaseAsyncStorage[APIKeyInDB]):
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
    await api_key_storage.drop()


@pytest.mark.asyncio
async def test_delete_api_key_ok(client: TestClient, auth_header, api_key_storage: BaseAsyncStorage[APIKeyInDB]):
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
        await api_key_storage.get(key_hash)


@pytest.mark.asyncio
async def test_delete_api_key_wrong_user(
    client: TestClient,
    auth_header,
    auth_header2,
    api_key_storage: BaseAsyncStorage[APIKeyInDB],
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
    st_key = await api_key_storage.get(key_hash)
    assert st_key.username == "test"
