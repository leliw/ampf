from pydantic import BaseModel

from ampf.in_memory import InMemoryFactory


class D(BaseModel):
    name: str
    value: str


def test_create_storage():
    # Given: A factory with a stroage with an item
    f = InMemoryFactory()
    s1 = f.create_storage("xxx", D)
    s1.drop()
    s1.save(D(name="1", value="a"))
    # When: The storage is created again
    s2 = f.create_storage("xxx", D)
    # Then: The item sill exists
    assert list(s2.keys()) == ["1"]
