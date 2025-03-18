import pytest

from ampf.base import BaseDecorator


def test_decorator():
    # Given: Decorated class C and its decorator D
    class C:
        def __init__(self) -> None:
            self.x = "x"

        def y(self) -> str:
            return "y"

        def echo(self, s: str) -> str:
            return s

        def a(self) -> str:
            return "a"

    class D(BaseDecorator[C]):
        def z(self) -> str:
            return "z"

        def a(self) -> str:
            return "a" + self.decorated.a()


    # When: Create decorated object
    d = D(C())
    # Then: Decorated class property is obtainable
    assert "x" == d.x
    # And: Decorated class method without parameters can be called
    assert "y" == d.y()
    # And: Decorated cladd method with parameters can be called
    assert "hop.hop" == d.echo("hop.hop")
    # And: Decorator class method without parameters can be called
    assert "z" == d.z()
    # And: Decorator class method can call decorated method
    assert "aa" == d.a()
    # And: Not existing calling method (neither decorated nor decrator) raise error
    with pytest.raises(AttributeError) as e:
        d.b()
    assert "'D' object has no attribute 'b'" == str(e.value)
