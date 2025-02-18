from typing import TypedDict

import pytest

import chz
from chz.mungers import attr_if_none, if_none


def test_munger():
    @chz.chz
    class A:
        a: int = chz.field(munger=lambda s, v: s.b)
        b: int = chz.field(munger=lambda s, v: s.c + 10)
        c: int = chz.field(munger=lambda s, v: s.X_a + 100)

    x = A(a=1, b=47, c=94)
    assert x.X_a == 1
    assert x.a == 111
    assert x.X_b == 47
    assert x.b == 111
    assert x.X_c == 94
    assert x.c == 101


def test_munger_call_count():
    count = 0

    def munger(s, v):
        nonlocal count
        count += 1
        return v * 2

    @chz.chz
    class A:
        a: int = chz.field(munger=munger)

    a = A(a=18)

    assert a.a == 36
    assert count == 1
    assert a.a == 36
    assert count == 1
    assert a.a == 36
    assert count == 1


def test_munger_conflict():
    with pytest.raises(
        ValueError, match="Cannot define 'a' in class when the associated field has a munger"
    ):

        @chz.chz
        class A:
            X_a: int = chz.field(munger=lambda s, v: s.X_a)

            @chz.init_property
            def a(self):
                return 1


def test_munge_recursive():
    @chz.chz
    class A:
        # Since we pass the value, there is little need to do this
        # And if there is need, it's still better to do s.X_a
        # We could make this a different kind of error other than RecursionError, but seems fine
        a: int = chz.field(munger=lambda s, v: s.a)

    with pytest.raises(RecursionError):
        A(a=1)


def test_munger_combinators():
    @chz.chz
    class A:
        a: int = chz.field(munger=if_none(lambda self: self.c))
        b: int = chz.field(munger=attr_if_none("a"))
        c: int = 42

    a = A(a=None, b=None)
    assert a.a == 42
    assert a.b == 42

    a = A(a=1, b=None)
    assert a.a == 1
    assert a.b == 1

    a = A(a=None, b=2)
    assert a.a == 42
    assert a.b == 2

    a = A(a=1, b=2)
    assert a.a == 1
    assert a.b == 2


def test_munger_x_type():
    @chz.chz(typecheck=True)
    class A:
        a: int = chz.field(munger=lambda s, v: int(v + "0") + 1, x_type=str)

    a = A(a="123")
    assert a.X_a == "123"
    assert a.a == 1231

    a = chz.Blueprint(A).apply({"a": chz.blueprint.Castable("456")}).make()
    assert a.X_a == "456"
    assert a.a == 4561

    @chz.chz(typecheck=True)
    class B:
        b: int = chz.field(munger=lambda s, v: v, x_type=str)

    with pytest.raises(TypeError, match="Expected X_b to be str, got int"):
        B(b=0)

    B(b="0")  # TODO: this could raise

    @chz.chz(typecheck=True)
    class C:
        X_c: int

        @chz.init_property
        def c(self) -> str:
            return str(self.X_c)

    assert C(c=0).c == "0"


def test_munger_freeze_dict():
    class MyDict(TypedDict):
        a: int
        b: int

    @chz.chz
    class A:
        d: dict[str, int] = chz.field(munger=chz.mungers.freeze_dict())
        d2: MyDict = chz.field(munger=chz.mungers.freeze_dict())

    x = A(d={"a": 1, "b": 2}, d2=MyDict(a=1, b=2))
    hash(x)
