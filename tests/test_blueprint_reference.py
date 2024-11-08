import pytest

import chz
from chz.blueprint import InvalidBlueprintArg, Reference


def test_blueprint_reference():
    @chz.chz
    class Main:
        a: str
        b: str

    obj = chz.Blueprint(Main).apply({"a": "foo", "b": Reference("a")}).make()
    assert obj == Main(a="foo", b="foo")

    obj = chz.Blueprint(Main).apply_from_argv(["a=foo", "b@=a"]).make()
    assert obj == Main(a="foo", b="foo")

    assert (
        chz.Blueprint(Main).apply({"a": "foo", "b": Reference("a")}).get_help()
        == """\
Entry point: test_blueprint_reference:test_blueprint_reference.<locals>.Main

Arguments:
  a  str  'foo'
  b  str  @=a
"""
    )

    with pytest.raises(InvalidBlueprintArg, match=r"Invalid reference target 'c' for b"):
        chz.Blueprint(Main).apply({"a": "foo", "b": Reference("c")}).make()


def test_blueprint_reference_nested():
    @chz.chz
    class C:
        c: int

    @chz.chz
    class B:
        b: int
        c: C

    @chz.chz
    class A:
        a: int
        b: B

    obj = chz.Blueprint(A).apply_from_argv(["a@=b.b", "b.c.c@=a", "b.b=5"]).make()
    assert obj == A(a=5, b=B(b=5, c=C(c=5)))


def test_blueprint_reference_wildcard():
    @chz.chz
    class B:
        name: str

    @chz.chz
    class A:
        name: str
        b: B

    @chz.chz
    class Main:
        name: str
        a: A

    obj = chz.Blueprint(Main).apply_from_argv(["...name@=name", "name=foo"]).make()
    assert obj == Main(name="foo", a=A(name="foo", b=B(name="foo")))

    obj = chz.Blueprint(Main).apply_from_argv(["...name@=a.b.name", "a.b.name=foo"]).make()
    assert obj == Main(name="foo", a=A(name="foo", b=B(name="foo")))
