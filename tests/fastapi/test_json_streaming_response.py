import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ampf.fastapi import JsonStreamingResponse


class Ret(BaseModel):
    hello: str = "Hello"


def test_sync_iterator():
    # When: Endpoint use sync iterator
    app = FastAPI()

    @app.get("/")
    def read_root():
        return JsonStreamingResponse([Ret()])

    client = TestClient(app)
    # And: The enpoint is called
    response = client.get("/")
    # Then: The response status code is 200
    assert 200 == response.status_code
    # And: The response contains right answer
    r = response.json()
    assert 1 == len(r)
    assert "Hello" == r[0]["hello"]


def test_async_iterator():
    # When: Endpoint use async iterator
    app = FastAPI()

    async def async_generator(data):
        for item in data:
            await asyncio.sleep(0)  # Simulate async operation
            yield item

    @app.get("/")
    def read_root():
        return JsonStreamingResponse(async_generator([Ret()]))

    client = TestClient(app)
    # And: The enpoint is called
    response = client.get("/")
    # Then: The response status code is 200
    assert 200 == response.status_code
    # And: The response contains right answer
    r = response.json()
    assert 1 == len(r)
    assert "Hello" == r[0]["hello"]


def test_exception_in_iterator():
    # When: Endpoint use sync iterator which raise exception
    app = FastAPI()

    def sync_generator(data):
        for item in data:
            yield item
        raise Exception("test")

    @app.get("/")
    def read_root():
        return JsonStreamingResponse(sync_generator([Ret()]))

    client = TestClient(app)
    # And: The enpoint is called
    response = client.get("/")
    # Then: The response status code is 200
    assert 200 == response.status_code
    # And: The response contains answer and exception
    r = response.json()
    assert 2 == len(r)
    assert "Hello" == r[0]["hello"]
    # And: The response contains exception with arguments
    assert "Exception" == r[1]["error"]
    assert "test" == r[1]["args"][0]
