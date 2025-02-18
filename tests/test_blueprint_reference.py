import pytest

import chz
from chz.blueprint import InvalidBlueprintArg, MissingBlueprintArg, Reference


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

    with pytest.raises(InvalidBlueprintArg, match=r"Invalid reference target 'c' for param b"):
        chz.Blueprint(Main).apply({"a": "foo", "b": Reference("c")}).make()


def test_blueprint_reference_multiple_invalid():
    @chz.chz
    class Main:
        a: int
        b: int
        c: int

    with pytest.raises(
        InvalidBlueprintArg,
        match="""\
Invalid reference target 'x' for params a, b

Invalid reference target 'bb' for param c
Did you mean 'b'?""",
    ):
        chz.Blueprint(Main).apply_from_argv(["a@=x", "b@=x", "c@=bb"]).make()


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


def test_blueprint_reference_wildcard_default():
    @chz.chz
    class A:
        name: str

    @chz.chz
    class Main:
        name: str = "foo"
        a: A

    obj = chz.Blueprint(Main).apply_from_argv(["...name@=name"]).make()
    assert obj == Main(name="foo", a=A(name="foo"))


def test_blueprint_reference_wildcard_default_no_default():
    @chz.chz
    class Defaults:
        a: int

    @chz.chz
    class A:
        defaults: Defaults
        a: int

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): defaults.a"
    ):
        chz.Blueprint(A).apply_from_argv(["...a@=defaults.a"]).make()


def test_blueprint_reference_wildcard_default_constructable():
    @chz.chz
    class Object:
        a: int = 1

    @chz.chz
    class Defaults:
        obj: Object
        a: int = 2

    @chz.chz
    class Main:
        defaults: Defaults
        obj: Object
        a: int = 3

    assert chz.Blueprint(Main).apply_from_argv(
        ["...obj@=defaults.obj", "defaults.obj.a=4"]
    ).make() == Main(
        defaults=Defaults(obj=Object(a=4), a=2),
        obj=Object(a=4),
        a=3,
    )

    assert chz.Blueprint(Main).apply_from_argv(["...obj@=defaults.obj", "...a=4"]).make() == Main(
        defaults=Defaults(obj=Object(a=4), a=4),
        obj=Object(a=4),
        a=4,
    )


def test_blueprint_reference_cycle():
    @chz.chz
    class Main:
        a: int
        b: int

    with pytest.raises(RecursionError, match="Detected cyclic reference: a -> b -> a"):
        chz.Blueprint(Main).apply_from_argv(["a@=b", "b@=a"]).make()

    @chz.chz
    class Main:
        a: int

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): a"
    ):
        chz.Blueprint(Main).apply_from_argv(["a@=a"]).make()
