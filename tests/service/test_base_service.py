import pytest
import respx
from httpx import Response, RequestError
from pydantic import BaseModel
from unittest.mock import AsyncMock, MagicMock
from ampf.service.base_service import BaseService

class SampleModel(BaseModel):
    name: str
    value: int

@pytest.fixture
def token_manager_mock():
    mock = MagicMock()
    mock.get_token_for = MagicMock(return_value="sync_token")
    mock.get_token_for_async = AsyncMock(return_value="async_token")
    return mock

@pytest.fixture
def service(token_manager_mock):
    return BaseService(
        base_url="https://api.example.com",
        token_manager=token_manager_mock
    )

@pytest.mark.asyncio
async def test_get_headers_async_with_token(service):
    headers = await service._get_headers_async()
    assert headers["Authorization"] == "Bearer async_token"
    service.token_manager.get_token_for_async.assert_called_once_with(service.base_url)

@pytest.mark.asyncio
async def test_get_headers_async_localhost():
    local_service = BaseService(base_url="http://localhost:8000")
    headers = await local_service._get_headers_async()
    assert headers == {}

@respx.mock
@pytest.mark.asyncio
async def test_get_request(service):
    route = respx.get("https://api.example.com/data").mock(return_value=Response(200, json={"status": "ok"}))
    
    response = await service.get("/data", params={"q": "test"})
    
    assert route.called
    assert response.json() == {"status": "ok"}
    assert route.calls.last.request.url.params["q"] == "test"

@respx.mock
@pytest.mark.asyncio
async def test_post_request_with_pydantic(service):
    route = respx.post("https://api.example.com/create").mock(return_value=Response(201))
    model = SampleModel(name="test", value=123)
    
    response = await service.post("/create", json=model)
    
    assert route.called
    assert route.calls.last.request.content == b'{"name":"test","value":123}'
    assert response.status_code == 201

@respx.mock
@pytest.mark.asyncio
async def test_ping_success(service):
    respx.get("https://api.example.com/api/ping").mock(return_value=Response(200))
    
    # Nie powinno rzucić wyjątku
    await service.ping()

@respx.mock
@pytest.mark.asyncio
async def test_ping_retries_on_500(service, monkeypatch):
    # Skracamy czas oczekiwania w testach
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    
    respx.get("https://api.example.com/api/ping").side_effect = [
        Response(500),
        Response(500),
        Response(200)
    ]
    
    await service.ping()
    assert len(respx.mock.calls) == 3

@respx.mock
@pytest.mark.asyncio
async def test_ping_raises_timeout_after_max_retries(service, monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    respx.get("https://api.example.com/api/ping").side_effect = RequestError("Conn error")
    
    with pytest.raises(TimeoutError) as excinfo:
        await service.ping()
    
    assert "timed out" in str(excinfo.value)
