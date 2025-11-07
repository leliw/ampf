from pydantic import BaseModel


class D(BaseModel):
    name: str

    def set_name(self, name: str) -> str:
        self.name = name
        return name


def test_skip_call(mock_method):
    # Given: An object with method
    obj = D(name="test")
    # When: I mock the methon
    mock_method(obj.set_name)
    # And: I call it
    obj.set_name("test2")
    # Then: The method is not called
    assert obj.name == "test"

def test_return_value(mock_method):
    # Given: An object with method
    obj = D(name="test")
    # When: I mock the methon
    mock_method(obj.set_name, return_value="test2")
    # And: I call it
    ret = obj.set_name("test2")
    # Then: The method is not called
    assert obj.name == "test"
    # And: Return value is different
    assert ret == "test2"

def test_side_effect(mock_method):
    # Given: An object with method
    obj = D(name="test")
    # When: I mock the methon
    mock_method(obj.set_name, side_effect=lambda name: name + "!")
    # And: I call it
    ret = obj.set_name("test2")
    # Then: The method is not called
    assert obj.name == "test"
    # And: Return value is different
    assert ret == "test2!"

