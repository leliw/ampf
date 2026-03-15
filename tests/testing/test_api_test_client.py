from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from ampf.testing.api_test_client import ApiTestClient


class DPatch(BaseModel):
    name: str | None = None
    value: str | None = None


class D(BaseModel):
    name: str
    value: str | None = None

    def patch(self, value_patch: DPatch) -> None:
        patch_dict = value_patch.model_dump(include=value_patch.model_fields_set)
        for field, value in patch_dict.items():
            setattr(self, field, value)


@pytest.fixture
def app():
    app = FastAPI()

    @app.get("/")
    async def root_get():
        return D(name="foo", value="bar")

    @app.get("/list")
    async def list_get():
        return [D(name="foo", value="bar")]

    @app.post("/")
    async def root_post(d: D):
        return d

    @app.post("/list")
    async def list_post(d: D):
        return [d]

    @app.put("/")
    async def root_put(d: D):
        return d

    @app.patch("/")
    async def root_patch(value_patch: DPatch):
        d = D(name="not_set", value="not_set")
        d.patch(value_patch)
        return d

    @app.delete("/")
    async def root_delete():
        return {"message": "deleted"}

    @app.get("/topic/message")
    async def get_topic_message():
        return D(name="topic", value="message")
    
    return app


@pytest.fixture
def client(app: FastAPI) -> ApiTestClient:  # type: ignore
    yield ApiTestClient(app)  # type: ignore


def test_get_status(client: ApiTestClient):
    # When: Call the get method with an expected status code
    client.get("/", 200)
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the get method with an unexpected status code
        # Then: It is not ok
        client.get("/", 400)


def test_get_typed(client: ApiTestClient):
    # When: Call the get_typed method with a Pydantic model
    ret = client.get_typed("/", 200, D)
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
    assert ret.name == "foo"
    assert ret.value == "bar"


def test_get_typed_list(client: ApiTestClient):
    # When: Call the get_list method with a Pydantic model
    ret = client.get_typed_list("/list", 200, D)
    # Then: The response is a list of correctly typed Pydantic models
    assert isinstance(ret, list)
    assert len(ret) == 1
    assert isinstance(ret[0], D)
    assert ret[0].name == "foo"
    assert ret[0].value == "bar"


def test_get_typed_list_err(client: ApiTestClient):
    # When: Call the get_list method with a non-list response
    # Then: It raises a ValueError
    with pytest.raises(ValueError):
        client.get_typed_list("/", 200, D)


def test_post_status(client: ApiTestClient):
    # When: Call the post method with an expected status code
    client.post("/", status_code=200, json=D(name="foo", value="bar"))
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the post method with an unexpected status code
        # Then: It is not ok
        client.post("/", status_code=400, json=D(name="foo", value="bar"))


def test_post_data(client: ApiTestClient):
    # When: Call the post method with an expected status code
    client.post("/", status_code=200, json=D(name="foo", value="bar"))
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the post method with an unexpected status code
        # Then: It is not ok
        client.post("/", status_code=400, json=D(name="foo", value="bar"))


def test_post_typed(client: ApiTestClient):
    # When: Call the post_typed method with a Pydantic model
    ret = client.post_typed("/", status_code=200, ret_clazz=D, json=D(name="foo", value="bar"))
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
    assert ret.name == "foo"
    assert ret.value == "bar"


def test_post_typed_list(client: ApiTestClient):
    # When: Call the post_typed method with a Pydantic model
    ret = client.post_typed_list("/list", status_code=200, ret_clazz=D, json=D(name="foo", value="bar"))
    # Then: The response is a list of correctly typed Pydantic models
    assert isinstance(ret, list)
    assert len(ret) == 1
    assert isinstance(ret[0], D)
    assert ret[0].name == "foo"
    assert ret[0].value == "bar"


def test_put_status(client: ApiTestClient):
    # When: Call the put method with an expected status code
    client.put("/", status_code=200, json=D(name="foo", value="bar"))
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the put method with an unexpected status code
        # Then: It is not ok
        client.put("/", status_code=400, json=D(name="foo", value="bar"))


def test_put_typed(client: ApiTestClient):
    # When: Call the put_typed method with a Pydantic model
    ret = client.put_typed("/", status_code=200, ret_clazz=D, json=D(name="foo", value="bar"))
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
    assert ret.name == "foo"
    assert ret.value == "bar"


def test_patch_status(client: ApiTestClient):
    # When: Call the put method with an expected status code
    client.patch("/", status_code=200, json=D(name="foo", value="bar"))
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the put method with an unexpected status code
        # Then: It is not ok
        client.put("/", status_code=400, json=D(name="foo", value="bar"))


def test_patch_typed(client: ApiTestClient):
    # When: Call the put_typed method with a Pydantic model
    ret = client.patch_typed("/", status_code=200, ret_clazz=D, json=D(name="foo", value="bar"))
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
    assert ret.name == "foo"
    assert ret.value == "bar"


def test_patch_not_set(client: ApiTestClient):
    # When: Call the put_typed method without optional field
    ret = client.patch_typed("/", status_code=200, ret_clazz=DPatch, json=DPatch(name="foo"))
    # Then: value isn't changed
    assert ret.value == "not_set"

def test_patch_none_set(client: ApiTestClient):
    # When: Call the put_typed method with optional field set to None
    ret = client.patch_typed("/", status_code=200, ret_clazz=DPatch, json=DPatch(name="foo", value=None))
    # Then: Value is changed to None
    assert ret.value is None


def test_delete_status(client: ApiTestClient):
    # When: Call the delete method with an expected status code
    client.delete("/", status_code=200)
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the delete method with an unexpected status code
        # Then: It is not ok
        client.delete("/", status_code=400)


def test_get_path_str(client: ApiTestClient):
    # When: Call the get_typed method with a str patch
    ret = client.get_typed("/topic/message", 200, D)
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
    assert ret.name == "topic"
    assert ret.value == "message"

def test_get_path(client: ApiTestClient):
    # When: Call the get_typed method with a Path patch
    ret = client.get_typed(Path("/topic/message"), 200, D)
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
    assert ret.name == "topic"
    assert ret.value == "message"
