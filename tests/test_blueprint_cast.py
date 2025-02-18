# Note test_blueprint_meta_factory.py also contains tests relevant to casting
from typing import Literal

import pytest

import chz
from chz.blueprint import Castable, InvalidBlueprintArg
from chz.tiepin import CastError


def test_castable():
    @chz.chz
    class A:
        a: bool | Literal["both"]

    assert chz.Blueprint(A).apply({"a": Castable("True")}).make() == A(a=True)
    assert chz.Blueprint(A).apply({"a": Castable("False")}).make() == A(a=False)
    assert chz.Blueprint(A).apply({"a": Castable("both")}).make() == A(a="both")

    with pytest.raises(
        InvalidBlueprintArg,
        match=r"Could not cast 'maybe' to Union\[bool, Literal\['both'\]\]",
    ):
        assert chz.Blueprint(A).apply({"a": Castable("maybe")}).make()

    @chz.chz
    class B:
        b: str | None

    assert chz.Blueprint(B).apply({"b": Castable("None")}).make() == B(b=None)
    assert chz.Blueprint(B).apply({"b": Castable("Nona")}).make() == B(b="Nona")

    @chz.chz
    class C:
        a: tuple[int, ...]
        b: tuple[str, int, str | None]

    assert chz.Blueprint(C).apply({"a": Castable("1,2,3"), "b": Castable("1,2,None")}).make() == C(
        a=(1, 2, 3), b=("1", 2, None)
    )
    assert chz.Blueprint(C).apply({"a": Castable("1,2,3"), "b": Castable("1,2,3")}).make() == C(
        a=(1, 2, 3), b=("1", 2, "3")
    )
    with pytest.raises(
        InvalidBlueprintArg,
        match=(
            "- Failed to interpret it as a value:\n"
            r"Could not cast '1,2,3,4' to tuple\[str, int, str \| None\] because of length mismatch"
            "\n\n- Failed to interpret it as a factory for polymorphic construction:\n"
            r"No subclass of tuple\[str, int, str \| None\] named '1,2,3,4' \(invalid identifier\)"
        ),
    ):
        assert chz.Blueprint(C).apply({"a": (1,), "b": Castable("1,2,3,4")}).make()
    with pytest.raises(
        InvalidBlueprintArg, match=r"No subclass of tuple\[int, \.\.\.\] named 'asdf'"
    ):
        assert chz.Blueprint(C).apply({"a": Castable("asdf"), "b": ("1", 2, "3")}).make()

    @chz.chz
    class D:
        a: Literal["a", 123]

    assert chz.Blueprint(D).apply({"a": Castable("a")}).make() == D(a="a")
    assert chz.Blueprint(D).apply({"a": Castable("123")}).make() == D(a=123)
    with pytest.raises(InvalidBlueprintArg, match=r"Could not cast 'b' to Literal\['a', 123\]"):
        assert chz.Blueprint(D).apply({"a": Castable("b")}).make()


def test_castable_object_str():
    @chz.chz
    class A:
        a: object

    assert chz.Blueprint(A).apply({"a": Castable("1")}).make() == A(a=1)
    assert chz.Blueprint(A).apply({"a": Castable("1a")}).make() == A(a="1a")


def test_meta_factory_cast_unspecified():
    @chz.chz
    class Base:
        value: int
        cls: int = 0

        @classmethod
        def __chz_cast__(cls, data: str):  # noqa: ANN206
            return Base(value=int(data))

    @chz.chz
    class DefaultChild(Base):
        value: int
        cls: int = 2

        @classmethod
        def __chz_cast__(cls, data: str):  # noqa: ANN206
            return DefaultChild(value=int(data))

    @chz.chz
    class X:
        a: Base = chz.field(
            meta_factory=chz.factories.subclass(base_cls=Base, default_cls=DefaultChild)
        )

    assert chz.Blueprint(X).apply({"a": Castable("3")}).make() == X(a=DefaultChild(value=3, cls=2))


def test_chz_cast_dunder():
    from dataclasses import dataclass

    @dataclass
    class Duration:
        seconds: int

        @classmethod
        def __chz_cast__(cls, value: str):  # noqa: ANN206
            try:
                return Duration(int(value.strip("hms")) * {"h": 3600, "m": 60, "s": 1}[value[-1]])
            except Exception as e:
                raise CastError(f"Could not cast {value!r} to {cls.__name__}") from e

    @chz.chz
    class X:
        t: Duration

    assert chz.Blueprint(X).apply({"t": Castable("1h")}).make() == X(t=Duration(3600))
    assert chz.Blueprint(X).apply({"t": Castable("1m")}).make() == X(t=Duration(60))
    with pytest.raises(
        InvalidBlueprintArg,
        match="Failed to interpret it as a value:\nCould not cast 'yikes' to Duration",
    ):
        chz.Blueprint(X).apply({"t": Castable("yikes")}).make()

    @chz.chz
    class Y:
        t1: str | Duration
        t2: Duration | str
        t3: str | Duration
        t4: Duration | str

    assert chz.Blueprint(Y).apply(
        {
            "t1": Castable("1h"),
            "t2": Castable("1m"),
            "t3": Castable("yikes"),
            "t4": Castable("yikes"),
        }
    ).make() == Y(t1=Duration(3600), t2=Duration(60), t3="yikes", t4="yikes")


def test_cast_per_field():
    @chz.chz
    class X:
        a: str = chz.field(blueprint_cast=lambda x: x[0])
        b: str = chz.field(blueprint_cast=lambda x: x[1])

    assert chz.Blueprint(X).apply({"a": Castable("abc"), "b": Castable("abc")}).make() == X(
        a="a", b="b"
    )
