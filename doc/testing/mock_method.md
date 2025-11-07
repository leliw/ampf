# mock_method

It is a simmple fixutre using `MockerFixture` for mocking methods and functions.

## Parameters

* `method: Callable` - Method to mock.
* `return_value: Optional[Any]` - Return value for the mocked method.
* `side_effect: Optional[Callable]` - Side effect for the mocked method.
* `*args`
* `**kwargs`

## Usage

Mocked class:

```python
class D(BaseModel):
    name: str

    def set_name(self, name: str) -> str:
        self.name = name
        return name
```

Just skip calling method without any changes:

```python
def test_skip_call(mock_method):
    obj = D(name="test")
    mock_method(obj.set_name)
    obj.set_name("test2")
    assert obj.name == "test"
```

Specify `return_value` to return a defined value:

```python
def test_return_value(mock_method):
    obj = D(name="test")
    mock_method(obj.set_name, return_value="test2")
    ret = obj.set_name("test2")
    assert obj.name == "test"
    assert ret == "test2"
```

Specify `side_effect` to call an another function:

```python
def test_side_effect(mock_method):
    obj = D(name="test")
    mock_method(obj.set_name, side_effect=lambda name: name + "!")
    ret = obj.set_name("test2")
    assert obj.name == "test"
    assert ret == "test2!"
```
