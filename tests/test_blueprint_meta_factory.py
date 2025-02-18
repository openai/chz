import typing
from typing import Optional

import pytest

import chz
from chz.blueprint import Castable, InvalidBlueprintArg, MissingBlueprintArg


class A:
    pass


class B(A):
    pass


class C(B):
    pass


def test_meta_factory_subclass():
    @chz.chz
    class Main:
        obj: A = chz.field(meta_factory=chz.factories.subclass(base_cls=A, default_cls=A))

    argv = ["obj=A"]
    ret = chz.entrypoint(Main, argv=argv)
    assert type(ret.obj) is A

    # Test basic subclass functionality, ie B -> A
    argv = ["obj=B"]
    ret = chz.entrypoint(Main, argv=argv)
    assert type(ret.obj) is B

    # Test multiple inheritance, ie C -> B -> A
    argv = ["obj=C"]
    ret = chz.entrypoint(Main, argv=argv)
    assert type(ret.obj) is C


def test_meta_factory_subclass_limited():
    # Test that a subclass of B is not accepted
    @chz.chz
    class Main:
        obj: A = chz.field(meta_factory=chz.factories.subclass(base_cls=B, default_cls=A))

    argv = ["obj=A"]
    with pytest.raises(
        InvalidBlueprintArg,
        match=(
            "Failed to interpret it as a factory for polymorphic construction:\n"
            "No subclass of test_blueprint_meta_factory.B named 'A'"
        ),
    ):
        chz.entrypoint(Main, argv=argv)


def test_meta_factory_default_subclass():
    @chz.chz
    class Parent:
        required0: int

    @chz.chz
    class Child2(Parent):
        required2: int

    @chz.chz
    class Main:
        field: Parent = chz.field(meta_factory=chz.factories.subclass(Parent, default_cls=Child2))

    assert (chz.Blueprint(Main).apply({"field.required0": 0, "field.required2": 2}).make()) == Main(
        field=Child2(required0=0, required2=2)
    )
    assert (
        chz.Blueprint(Main)
        .apply({"field.required0": 0, "field": Child2, "field.required2": 2})
        .make()
    ) == Main(field=Child2(required0=0, required2=2))

    assert (
        chz.Blueprint(Main).apply({"field.required0": 0}).get_help()
        == """\
WARNING: Missing required arguments for parameter(s): field.required2

Entry point: test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Main

Arguments:
  field            test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Parent    test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Child2 (meta_factory)
  field.required0  int                                       0
  field.required2  int                                       -
"""
    )

    assert (
        chz.Blueprint(Main).apply({"field.required0": 0, "field": Child2}).get_help()
        == """\
WARNING: Missing required arguments for parameter(s): field.required2

Entry point: test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Main

Arguments:
  field            test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Parent    test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Child2
  field.required0  int                                       0
  field.required2  int                                       -
"""
    )

    @chz.chz
    class Main2:
        field: Parent | None = chz.field(
            meta_factory=chz.factories.subclass(Parent, default_cls=Child2), default=None
        )

    assert (
        chz.Blueprint(Main2).get_help()
        == """\
Entry point: test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Main2

Arguments:
  field            test_blueprint_meta_factory.test_meta_factory_default_subclass.<locals>.Parent | None                 None (default)
  field.required0  int                                       -
  field.required2  int                                       -
"""
    )

    assert (
        chz.Blueprint(Main2).apply({"field.required0": 0}).get_help()
        == """\
WARNING: Missing required arguments for parameter(s): field.required2

Entry point: test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Main2

Arguments:
  field            test_blueprint_meta_factory.test_meta_factory_default_subclass.<locals>.Parent | None                 test_blueprint_meta_factory:test_meta_factory_default_subclass.<locals>.Child2 (meta_factory)
  field.required0  int                                       0
  field.required2  int                                       -
"""
    )


def test_meta_factory_blueprint_unspecified():
    @chz.chz
    class Parent:
        required0: int

    @chz.chz
    class Child2(Parent):
        required2: int

    @chz.chz
    class Main:
        field: Parent = chz.field(blueprint_unspecified=Child2)

    assert (chz.Blueprint(Main).apply({"field.required0": 0, "field.required2": 2}).make()) == Main(
        field=Child2(required0=0, required2=2)
    )
    assert (
        chz.Blueprint(Main)
        .apply({"field.required0": 0, "field": Child2, "field.required2": 2})
        .make()
    ) == Main(field=Child2(required0=0, required2=2))

    assert (
        chz.Blueprint(Main).get_help()
        == """\
WARNING: Missing required arguments for parameter(s): field.required0, field.required2

Entry point: test_blueprint_meta_factory:test_meta_factory_blueprint_unspecified.<locals>.Main

Arguments:
  field            test_blueprint_meta_factory:test_meta_factory_blueprint_unspecified.<locals>.Parent                   test_blueprint_meta_factory:test_meta_factory_blueprint_unspecified.<locals>.Child2 (blueprint_unspecified)
  field.required0  int                                       -
  field.required2  int                                       -
"""
    )


def test_meta_factory_blueprint_unspecified_more():
    @chz.chz
    class Sub:
        x: int = 1

    @chz.chz
    class Config:
        sub: Sub
        sub2: Sub

    @chz.chz
    class MySub(Sub):
        x: int = 2

    @chz.chz
    class MySub2(Sub):
        x: int = 3

    @chz.chz
    class MyConfig(Config):
        sub: Sub = chz.field(blueprint_unspecified=MySub)
        sub2: Sub = chz.field(blueprint_unspecified=MySub2)

    # Check defaults get overwritten properly
    config = chz.Blueprint(MyConfig).make()
    assert config == MyConfig(sub=MySub(x=2), sub2=MySub2(x=3))

    # Check you can still set the nested values properly
    config = chz.Blueprint(MyConfig).apply_from_argv(["sub.x=4", "sub2.x=5"]).make()
    assert config == MyConfig(sub=MySub(x=4), sub2=MySub2(x=5))

    # Ensure that's okay to override a field with the base Sub class
    config = chz.Blueprint(MyConfig).apply_from_argv(["sub=Sub"]).make()
    assert config == MyConfig(sub=Sub(x=1), sub2=MySub2(x=3))

    # Lastly, check that it's okay to override the fields with custom Sub classes
    config = chz.Blueprint(MyConfig).apply_from_argv(["sub=MySub2", "sub2=MySub"]).make()
    assert config == MyConfig(sub=MySub2(x=3), sub2=MySub(x=2))


def test_meta_factory_blueprint_unspecified_all_default_help():
    @chz.chz
    class X:
        value: int = 0

    @chz.chz
    class Main:
        field: object = chz.field(blueprint_unspecified=X)

    assert (
        chz.Blueprint(Main).get_help()
        == """\
Entry point: test_blueprint_meta_factory:test_meta_factory_blueprint_unspecified_all_default_help.<locals>.Main

Arguments:
  field        object  test_blueprint_meta_factory:test_meta_factory_blueprint_unspecified_all_default_help.<locals>.X (meta_factory)
  field.value  int     0 (default)
"""
    )


def test_meta_factory_blueprint_unspecified_optional():
    @chz.chz
    class X:
        value: int = 0

    @chz.chz
    class Main:
        value: int = 0
        field: X | None = chz.field(blueprint_unspecified=X, default=None)

    assert chz.Blueprint(Main).apply({"...value": 1}).make() == Main(value=1, field=X(value=1))

    @chz.chz
    class Main:
        value: int = 0
        field: X | None = chz.field(blueprint_unspecified=type(None), default=None)

    assert chz.Blueprint(Main).apply({"...value": 1}).make() == Main(value=1, field=None)


def test_meta_factory_subclass_generic():
    T = typing.TypeVar("T")

    @chz.chz
    class Base(typing.Generic[T]):
        pass

    @chz.chz
    class Sub(Base[int]):
        value: int = 0

    @chz.chz
    class Main1:
        obj: Base

    argv = ["obj=Base"]
    ret = chz.entrypoint(Main1, argv=argv)
    assert type(ret.obj) is Base

    argv = ["obj=Sub"]
    ret = chz.entrypoint(Main1, argv=argv)
    assert type(ret.obj) is Sub

    @chz.chz
    class Main2:
        obj: Base[int]

    argv = ["obj=Base"]
    ret = chz.entrypoint(Main2, argv=argv)
    assert type(ret.obj) is Base

    argv = ["obj=Sub"]
    ret = chz.entrypoint(Main2, argv=argv)
    assert type(ret.obj) is Sub

    argv = ["obj=Sub", "obj.value=3"]
    ret = chz.entrypoint(Main2, argv=argv)
    assert type(ret.obj) is Sub
    assert ret.obj.value == 3


def test_meta_factory_optional():
    @chz.chz
    class Child2:
        x: int

    @chz.chz
    class Parent:
        child: Optional[Child2]  # noqa: UP045

    @chz.chz
    class Parent2:
        child: Child2 | None

    assert chz.Blueprint(Parent).apply({"child.x": 3}).make() == Parent(child=Child2(x=3))
    assert chz.Blueprint(Parent2).apply({"child.x": 3}).make() == Parent2(child=Child2(x=3))


def test_meta_factory_union():
    from dataclasses import dataclass

    @dataclass
    class O1: ...

    @dataclass
    class O2: ...

    @chz.chz
    class Main:
        z: O1 | O2

    assert chz.Blueprint(Main).apply({"z": Castable("O1")}).make() == Main(z=O1())
    assert chz.Blueprint(Main).apply({"z": Castable("O2")}).make() == Main(z=O2())


def test_meta_factory_non_chz():
    class Actor:
        def __init__(self):
            self.label = "actor"

    class WakeActor(Actor):
        def __init__(self):
            self.label = "wake_actor"

    @chz.chz
    class Args:
        actor: Actor = chz.field(meta_factory=chz.factories.subclass(Actor))

    assert chz.Blueprint(Args).apply({"actor": Castable("Actor")}).make().actor.label == "actor"
    assert (
        chz.Blueprint(Args).apply({"actor": Castable("WakeActor")}).make().actor.label
        == "wake_actor"
    )

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): actor"
    ):
        chz.Blueprint(Args).make()


def test_meta_factory_function_lambda():
    import calendar

    @chz.chz
    class Main:
        a: A = chz.field(meta_factory=chz.factories.function(), default=object())
        cal: calendar.Calendar = chz.field(
            meta_factory=chz.factories.function(default_module="calendar"), default=object()
        )

    argv = ["a=lambda: A()", "cal=lambda d: Calendar(int(d))", "cal.d=3"]
    ret = chz.entrypoint(Main, argv=argv)
    assert type(ret.a) is A
    assert type(ret.cal) is calendar.Calendar
    assert ret.cal.firstweekday == 3

    @chz.chz
    class Main:
        a: A = chz.field(default=object())
        cal: calendar.Calendar = chz.field(
            meta_factory=chz.factories.standard(default_module="calendar"), default=object()
        )

    argv = ["a=lambda: A()", "cal=lambda d: Calendar(int(d))", "cal.d=3"]
    ret = chz.entrypoint(Main, argv=argv)
    assert type(ret.a) is A
    assert type(ret.cal) is calendar.Calendar
    assert ret.cal.firstweekday == 3


def test_meta_factory_type_subclass():
    @chz.chz
    class Main:
        a: type[A]

    assert chz.entrypoint(Main, argv=["a=A"]).a is A
    assert chz.entrypoint(Main, argv=["a=B"]).a is B
    assert chz.entrypoint(Main, argv=["a=C"]).a is C

    with pytest.raises(
        InvalidBlueprintArg, match="Could not interpret argument 'int' provided for param 'a'"
    ):
        chz.entrypoint(Main, argv=["a=int"])


def test_meta_factory_function_union():
    @chz.chz
    class A:
        field: str = "a"

    @chz.chz
    class B(A): ...

    def make_tuple(s0: B | None = None, s1: B | None = None):
        if s0 is None:
            s0 = B(field="s0default")
        if s1 is None:
            s1 = B(field="s1default")
        return (s0, s1)

    @chz.chz
    class Main:
        specs: tuple[A, ...] = chz.field(blueprint_unspecified=make_tuple)

    assert chz.entrypoint(Main, argv=["specs.s1=B"]).specs == (
        B(field="s0default"),
        B(field="a"),
    )


def test_meta_factory_none():
    @chz.chz
    class Main:
        a: A = chz.field(meta_factory=None)

    with pytest.raises(
        InvalidBlueprintArg, match="Could not cast 'A' to test_blueprint_meta_factory:A"
    ):
        chz.entrypoint(Main, argv=["a=A"])
