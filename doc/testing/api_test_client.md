# ApiTestClient

It extends `TestClient` for asserting status code and converting from/to Pydantic objects.

## Usage

Assert status code - just set the second parameter

```python
def test_get_status(client: ApiTestClient):
    # When: Call the get method with an expected status code
    client.get("/", 200)
    # Then: It is ok
    assert True
    with pytest.raises(AssertionError):
        # When: Call the get method with an unexpected status code
        # Then: It is not ok
        client.get("/", 400)
```

Convert to Pydantic object - set the third parameter

```python
def test_get_typed(client: ApiTestClient):
    # When: Call the get_typed method with a Pydantic model
    ret = client.get_typed("/", 200, D)
    # Then: The response is correctly typed
    assert isinstance(ret, D)

def test_get_list(client: ApiTestClient):
    # When: Call the get_list method with a Pydantic model
    ret = client.get_list("/list", 200, D)
    # Then: The response is a list of correctly typed Pydantic models
    assert isinstance(ret, list)
    assert isinstance(ret[0], D)
```

Convert from Pydantic object - set Pydantic object as `json` parameter.

```python
def test_post_status(client: ApiTestClient):
    # When: Call the post method with an expected status code
    client.post("/", status_code=200, json=D(name="foo", value="bar"))
    # Then: It is ok

def test_post_typed(client: ApiTestClient):
    # When: Call the post_typed method with a Pydantic model
    ret = client.post_typed("/", status_code=200, ret_clazz=D, json=D(name="foo", value="bar"))
    # Then: The response is correctly typed and contains the expected data
    assert isinstance(ret, D)
```
