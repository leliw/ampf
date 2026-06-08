import pytest
import respx
from httpx2 import Request, Response, RequestError, MockTransport
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

@pytest.mark.asyncio
async def test_get_request(service):
    def mock_send(request: Request) -> Response:
        assert request.url == "https://api.example.com/data?q=test"
        return Response(200, json={"status": "ok"})
    service.httpx_async_client._transport = MockTransport(mock_send)
    
    response = await service.get("/data", params={"q": "test"})
    
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_post_request_with_pydantic(service):
    def mock_send(request: Request) -> Response:
        assert request.method == "POST"
        assert request.url == "https://api.example.com/create"
        return Response(201)
    service.httpx_async_client._transport = MockTransport(mock_send)
    model = SampleModel(name="test", value=123)
    
    response = await service.post("/create", json=model)
    
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_ping_success(service):
    def mock_send(request: Request) -> Response:
        assert request.url == "https://api.example.com/api/ping"
        return Response(200)
    service.httpx_async_client._transport = MockTransport(mock_send)
    
    # Nie powinno rzucić wyjątku
    await service.ping()

@pytest.mark.asyncio
async def test_ping_retries_on_500(service, monkeypatch):
    call_count = 0
    def mock_send(request: Request) -> Response:
        assert request.url == "https://api.example.com/api/ping"
        nonlocal call_count
        call_count += 1
        return Response(500)
    service.httpx_async_client._transport = MockTransport(mock_send)    
    # Skracamy czas oczekiwania w testach
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    await service.ping()
    assert call_count == 5

@respx.mock
@pytest.mark.asyncio
async def test_ping_raises_timeout_after_max_retries(service, monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    respx.get("https://api.example.com/api/ping").side_effect = RequestError("Conn error")
    
    with pytest.raises(TimeoutError) as excinfo:
        await service.ping()
    
    assert "timed out" in str(excinfo.value)
