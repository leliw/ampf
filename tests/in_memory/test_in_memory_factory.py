from pydantic import BaseModel
from ampf.in_memory import InMemoryFactory


class D(BaseModel):
    name: str
    value: str


def test_create_storage():
    t1 = InMemoryFactory()
    s1 = t1.create_storage("xxx", D)
    s1.save(D(name="1", value="a"))

    t2 = InMemoryFactory()
    s2 = t2.create_storage("xxx", D)

    assert list(s2.keys()) == ["1"]
