import pytest

import chz
from chz.blueprint import Castable, ExtraneousBlueprintArg, InvalidBlueprintArg, MissingBlueprintArg


def test_entrypoint():
    def foo(a: int, b: str, c: float = 1.0):
        return locals()

    argv = ["a=1", "b=str", "c=5"]
    assert chz.entrypoint(foo, argv=argv) == foo(1, "str", 5)

    argv = ["a=1", "b=str"]
    assert chz.entrypoint(foo, argv=argv) == foo(1, "str", 1)

    # test allow_hyphens
    assert chz.entrypoint(foo, argv=argv, allow_hyphens=True) == foo(1, "str", 1)

    argv = ["--a=1", "--b=str", "c=5"]
    with pytest.raises(
        ExtraneousBlueprintArg,
        match=(
            r"Extraneous argument '--a' to Blueprint for test_blueprint.test_entrypoint.<locals>.foo \(from command line\)"
            "\nDid you mean to use allow_hyphens=True in your entrypoint?"
        ),
    ):
        chz.entrypoint(foo, argv=argv)
    assert chz.entrypoint(foo, argv=argv, allow_hyphens=True) == foo(1, "str", 5)

    # test positional
    argv = ["a", "1", "b", "str"]
    with pytest.raises(
        ValueError, match="Invalid argument 'a'. Specify arguments in the form key=value"
    ):
        chz.entrypoint(foo, argv=argv)


def test_entrypoint_nested():
    @chz.chz
    class X:
        a: int
        b: str
        c: float = 1.0

    def main(x: X) -> list[X]:
        return [x]

    argv = ["a=1", "b=str", "c=5"]
    assert chz.nested_entrypoint(main, argv=argv) == [X(a=1, b="str", c=5)]

    argv = ["a=1", "b=str"]
    assert chz.nested_entrypoint(main, argv=argv) == [X(a=1, b="str", c=1)]


def test_apply_strictness():
    """Test strictness of application when configured and non-strictness when not."""

    @chz.chz
    class X:
        hello: int = 5

    # misspelled! No error on application, but error on make.
    misspelled_bp = chz.Blueprint(X).apply({"hllo": 1})
    with pytest.raises(ExtraneousBlueprintArg):
        misspelled_bp.make()

    # In strict mode, we get an error on apply.
    with pytest.raises(ExtraneousBlueprintArg):
        chz.Blueprint(X).apply({"hllo": 1}, strict=True)


def test_basic_function_blueprint():
    def foo(a: int, b: int | str, c: bool = False, d: bytes = b""):
        return locals()

    # regular
    assert chz.Blueprint(foo).apply({"a": 1, "b": "str"}).make() == foo(1, "str", False, b"")
    # default
    assert chz.Blueprint(foo).apply({"a": 1, "b": "2", "c": True}).make() == foo(1, "2", True, b"")
    # clobbered
    assert chz.Blueprint(foo).apply({"a": 1, "b": "str"}).apply({"a": 2}).make() == foo(
        2, "str", False, b""
    )

    # castable
    assert chz.Blueprint(foo).apply(
        {"a": Castable("1"), "b": Castable("str"), "c": Castable("True")}
    ).make() == foo(1, "str", True, b"")

    with pytest.raises(TypeError, match="Expected 'a' to be int, got str"):
        chz.Blueprint(foo).apply({"a": "asdf"}).make()
    with pytest.raises(
        InvalidBlueprintArg,
        match=(
            "- Failed to interpret it as a value:\n"
            "Could not cast 'asdf' to int\n\n"
            "- Failed to interpret it as a factory for polymorphic construction:\n"
            "No subclass of int named 'asdf'"
        ),
    ):
        chz.Blueprint(foo).apply({"a": Castable("asdf")}).make()


def test_basic_class_blueprint():
    @chz.chz
    class X:
        a: int
        b: str

    # regular
    assert chz.Blueprint(X).apply({"a": 1, "b": "str"}).make() == X(a=1, b="str")
    # clobbered
    assert chz.Blueprint(X).apply({"a": 1, "b": "str"}).apply({"a": 2}).make() == X(a=2, b="str")

    # castable
    assert chz.Blueprint(X).apply({"a": Castable("1"), "b": "str"}).make() == X(a=1, b="str")

    with pytest.raises(TypeError, match="Expected 'a' to be int, got str"):
        chz.Blueprint(X).apply({"a": "asdf"}).make()
    with pytest.raises(
        InvalidBlueprintArg,
        match=(
            "- Failed to interpret it as a value:\n"
            "Could not cast 'asdf' to int\n\n"
            "- Failed to interpret it as a factory for polymorphic construction:\n"
            "No subclass of int named 'asdf'"
        ),
    ):
        chz.Blueprint(X).apply({"a": Castable("asdf")}).make()


def test_blueprint_unused():
    def foo(alpha: int, beta: str = ""):
        return locals()

    with pytest.raises(
        ExtraneousBlueprintArg,
        match="Extraneous argument 'missing' to Blueprint for test_blueprint.test_blueprint_unused.<locals>.foo",
    ):
        assert chz.Blueprint(foo).apply({"alpha": 1, "missing": "oops"}).make()

    @chz.chz
    class Foo:
        alpha: int
        beta: str

    assert chz.Blueprint(Foo).apply({"alpha": 1, "beta": "str"}).make() == Foo(alpha=1, beta="str")

    with pytest.raises(
        ExtraneousBlueprintArg,
        match="Extraneous argument 'missing' to Blueprint for test_blueprint.test_blueprint_unused.<locals>.Foo",
    ):
        assert chz.Blueprint(Foo).apply({"alpha": 1, "missing": "oops"}).make()

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean 'alpha'"):
        assert chz.Blueprint(Foo).apply({"alpha": 1, "aleph": "oops"}).make()

    @chz.chz
    class Bar:
        foo: Foo
        gamma: int

    assert (
        chz.Blueprint(Bar).apply({"foo.alpha": 1, "foo.beta": "str", "gamma": 1}).make()
    ) == Bar(foo=Foo(alpha=1, beta="str"), gamma=1)

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean 'foo\.alpha'"):
        assert (
            chz.Blueprint(Bar)
            .apply({"foo.alpha": 1, "foo.beta": "str", "foo.aleph": "oops"})
            .make()
        )
    with pytest.raises(
        ExtraneousBlueprintArg,
        match=r"Did you get the nesting wrong, maybe you meant 'foo.alpha'\?",
    ):
        assert (
            chz.Blueprint(Bar)
            .apply({"foo.alpha": 1, "foo.beta": "str", "alpha": "oops", "gamma": 1})
            .make()
        )

    assert (
        chz.Blueprint(Bar).apply({"...alpha": 1, "...beta": "str", "...gamma": 1}).make()
    ) == Bar(foo=Foo(alpha=1, beta="str"), gamma=1)

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean '\.\.\.alpha'"):
        assert chz.Blueprint(Bar).apply({"...alpha": 1, "...aleph": "oops"}).make()

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean '\.\.\.foo\.\.\.alpha'"):
        assert chz.Blueprint(Bar).apply({"...alpha": 1, "...foo...aleph": "oops"}).make()

    @chz.chz
    class Baz:
        bar: Bar
        delta: int

    assert (
        chz.Blueprint(Baz)
        .apply({"bar.foo.alpha": 1, "bar.foo.beta": "str", "bar.gamma": 1, "delta": 1})
        .make()
    ) == Baz(bar=Bar(foo=Foo(alpha=1, beta="str"), gamma=1), delta=1)

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean 'bar\.foo\.alpha'"):
        assert (
            chz.Blueprint(Baz)
            .apply({"bar.foo.alpha": 1, "bar.foo.beta": "str", "bar.foo.aleph": "oops"})
            .make()
        )

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean 'bar\.foo\.\.\.alpha'"):
        assert chz.Blueprint(Baz).apply({"...alpha": 1, "bar.foo...aleph": "oops"}).make()

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean '\.\.\.bar\.\.\.foo\.alpha'"):
        assert chz.Blueprint(Baz).apply({"...alpha": 1, "...bar...foo.aleph": "oops"}).make()

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean '\.\.\.bar\.\.\.foo\.alpha'"):
        assert chz.Blueprint(Baz).apply({"...alpha": 1, "...bar...foZ.aleph": "oops"}).make()


def test_blueprint_unused_nested_default():
    @chz.chz
    class Sub:
        alpha: int = 1
        beta: str = "str"

    @chz.chz
    class Main:
        sub: Sub
        gamma: int

    with pytest.raises(ExtraneousBlueprintArg, match=r"Did you mean 'sub\.beta'"):
        chz.Blueprint(Main).apply({"sub.bata": "str"}).make()


def test_blueprint_missing_args():
    @chz.chz
    class Alpha:
        alpha: int
        beta: str

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): alpha, beta"
    ):
        chz.Blueprint(Alpha).make()

    @chz.chz
    class Main:
        alpha: Alpha

    with pytest.raises(
        MissingBlueprintArg,
        match=r"Missing required arguments for parameter\(s\): alpha.alpha, alpha.beta",
    ):
        chz.Blueprint(Main).make()

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): alpha.beta"
    ):
        chz.Blueprint(Main).apply({"alpha.alpha": 1}).make()

    @chz.chz
    class MainDefault:
        alpha: Alpha = chz.field(default=Alpha(alpha=1, beta="str"))
        other: int

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): other"
    ):
        chz.Blueprint(MainDefault).make()


def three_item_dataset(first: str = "a", second: str = "b", third: str = "c") -> list[str]:
    return [first, second, third]


@chz.chz
class Model:
    family: str
    n_layers: int
    salt: bytes = b"salt"


@chz.chz
class Experiment:
    model: Model
    dataset: list[str] = chz.field(doc="Yummy data!")


def test_nested_construction():
    expected = Experiment(
        model=Model(family="linear", n_layers=1, salt=b"0000"), dataset=["a", "b", "c"]
    )
    assert (
        chz.Blueprint(Experiment)
        .apply(
            {
                "model.family": "linear",
                "model.n_layers": 1,
                "model.salt": b"0000",
                "dataset": ["a", "b", "c"],
            }
        )
        .make()
        == expected
    )


def test_nested_construction_with_default_value():
    expected = Experiment(
        model=Model(family="linear", n_layers=1, salt=b"salt"), dataset=["a", "b", "c"]
    )
    assert (
        chz.Blueprint(Experiment)
        .apply({"model.family": "linear", "model.n_layers": 1, "dataset": ["a", "b", "c"]})
        .make()
        == expected
    )


def test_nested_construction_with_factory_dataset():
    expected = Experiment(
        model=Model(family="linear", n_layers=1, salt=b"0000"), dataset=["first", "b", "third"]
    )
    assert (
        chz.Blueprint(Experiment)
        .apply(
            {
                "model.family": "linear",
                "model.n_layers": 1,
                "model.salt": b"0000",
                "dataset": three_item_dataset,
                "dataset.first": "first",
                "dataset.third": "third",
            }
        )
        .make()
        == expected
    )


def test_nested_construction_with_wildcards():
    expected = Experiment(
        model=Model(family="linear", n_layers=1, salt=b"0000"), dataset=["first", "b", "third"]
    )
    assert (
        chz.Blueprint(Experiment)
        .apply(
            {
                "...family": "linear",
                "...n_layers": 1,
                "...salt": b"0000",
                "...dataset": three_item_dataset,
                "...first": "first",
                "...third": "third",
            }
        )
        .make()
        == expected
    )

    assert (
        chz.Blueprint(Experiment)
        .apply(
            {
                "...family": "linear",
                "...n_layers": 1,
                "...salt": b"0000",
                "...dataset": Castable("three_item_dataset"),
                "dataset...first": "first",
                "...third": "third",
            }
        )
        .make()
        == expected
    )

    assert (
        chz.Blueprint(Experiment)
        .apply(
            {
                "...family": "linear",
                "...n_layers": 1,
                "...salt": b"0000",
                "...dataset": Castable("three_item_dataset"),
                "...dataset...first": "first",  # even more wildcard
                "...third": "third",
            }
        )
        .make()
        == expected
    )


def test_nested_all_defaults():
    @chz.chz
    class X:
        value: int = 0

    @chz.chz
    class Y:
        x: X
        y: int

    assert chz.Blueprint(Y).apply({"y": 5}).make() == Y(x=X(value=0), y=5)


def test_nested_not_all_defaults():
    @chz.chz
    class X:
        value: int

    @chz.chz
    class Y:
        x: X

    @chz.chz
    class Parent:
        child: Y | None = None

    assert chz.Blueprint(Parent).make() == Parent(child=None)


def test_nested_all_defaults_primitive():
    @chz.chz
    class X:
        value: int

    @chz.chz
    class Y:
        x: X | None = None

    assert chz.Blueprint(Y).make() == Y(x=None)


def test_nested_construction_with_default_factory():
    @chz.chz
    class ChildV1:
        required1: int

    @chz.chz
    class ChildV2:
        required2: int

    @chz.chz
    class Parent:
        child_v1: ChildV1 = chz.field(default_factory=lambda: ChildV1(required1=1))
        child_v2: ChildV2 = chz.field(default_factory=lambda: ChildV2(required2=2))

    assert chz.Blueprint(Parent).apply({}).make() == Parent(
        child_v1=ChildV1(required1=1), child_v2=ChildV2(required2=2)
    )


def test_help():
    assert (
        chz.Blueprint(Experiment).get_help()
        == """\
WARNING: Missing required arguments for parameter(s): model.family, model.n_layers, dataset

Entry point: test_blueprint:Experiment

Arguments:
  model           test_blueprint:Model  -
  model.family    str                   -
  model.n_layers  int                   -
  model.salt      bytes                 b'salt' (default)
  dataset         list[str]             -                  Yummy data!
"""
    )

    assert (
        chz.Blueprint(Experiment).apply({"model.family": "gpt"}, layer_name="gpt config").get_help()
        == """\
WARNING: Missing required arguments for parameter(s): model.n_layers, dataset

Entry point: test_blueprint:Experiment

Arguments:
  model           test_blueprint:Model  test_blueprint:Model (meta_factory)
  model.family    str                   'gpt' (from gpt config)
  model.n_layers  int                   -
  model.salt      bytes                 b'salt' (default)
  dataset         list[str]             -                                    Yummy data!
"""
    )

    @chz.chz
    class Foo:
        a: int = chz.field(default_factory=lambda: 1 + 1)

    assert (
        chz.Blueprint(Foo).get_help()
        == """\
Entry point: test_blueprint:test_help.<locals>.Foo

Arguments:
  a  int  (lambda: 1 + 1)() (default)
"""
    )

    assert (
        chz.Blueprint(Foo).apply({"a": Castable("2")}, layer_name="preset").get_help()
        == """\
Entry point: test_blueprint:test_help.<locals>.Foo

Arguments:
  a  int  2 (from preset)
"""
    )


def test_logical_name_blueprint():
    @chz.chz
    class X:
        X_seed1: int
        X_seed2: int

        @property
        def seed1(self):
            return self.X_seed1 + 100

        @property
        def seed2(self):
            return self.X_seed2 + 100

    x = chz.Blueprint(X).apply({"seed1": 1, "seed2": 2}).make()
    assert x.seed1 == 101
    assert x.seed2 == 102
    assert x == X(seed1=1, seed2=2)


def test_blueprint_unpack_kwargs():
    from typing import TypedDict, Unpack

    class Args(TypedDict):
        a: int
        b: str

    def foo(**kwargs: Unpack[Args]) -> Args:
        return Args(**kwargs)

    assert chz.Blueprint(foo).apply(
        {"a": chz.Castable("1"), "b": chz.Castable("2")}
    ).make() == Args(a=1, b="2")

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): b"
    ):
        chz.Blueprint(foo).apply({"a": 1}).make()


def test_blueprint_castable_but_subpaths():
    @chz.chz
    class A:
        field: str

    @chz.chz
    class Main:
        a: A = chz.field(blueprint_cast=lambda s: A(field=s))

    with pytest.raises(
        InvalidBlueprintArg,
        match=r"""Could not interpret argument 'works' provided for param 'a'...

- Failed to interpret it as a value:
Not a value, since subparameters were provided \(e.g. 'a.field'\)

- Failed to interpret it as a factory for polymorphic construction:
No subclass of test_blueprint:test_blueprint_castable_but_subpaths.<locals>.A named 'works'""",
    ):
        chz.Blueprint(Main).apply({"a": Castable("works"), "a.field": Castable("field")}).make()


def test_blueprint_apply_subpath():
    @chz.chz
    class A:
        field: int

    @chz.chz
    class AA:
        a: A

    @chz.chz
    class Main:
        a: AA
        field: int = 0

    assert chz.Blueprint(Main).apply({"field": 1}, subpath="a.a").make() == Main(
        a=AA(a=A(field=1)), field=0
    )

    assert chz.Blueprint(Main).apply({"...field": 1}, subpath="").make() == Main(
        a=AA(a=A(field=1)), field=1
    )
    assert chz.Blueprint(Main).apply({"...field": 1}, subpath="a").make() == Main(
        a=AA(a=A(field=1)), field=0
    )

    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument 'b.field' to Blueprint"):
        chz.Blueprint(Main).apply({"field": 1}, subpath="b").make()


def test_blueprint_enum_all_defaults():
    import enum

    class E(enum.StrEnum):
        foo = enum.auto()
        bar = enum.auto()

    @chz.chz
    class Inner:
        e: E = E.foo

    @chz.chz
    class Args:
        e: E = E.foo
        inner: Inner

    assert chz.Blueprint(Args).make() == Args(e=E.foo, inner=Inner(e=E.foo))
    assert chz.Blueprint(Args).apply({"inner.e": Castable("bar")}).make() == Args(
        e=E.foo, inner=Inner(e=E.bar)
    )


def test_blueprint_functools_partial():
    import functools

    def foo(a: int = 1, b: int = 2):
        return a, b

    partial_foo = functools.partial(foo, a=3, b=4)

    assert chz.Blueprint(partial_foo).apply({"a": 5}).make() == (5, 4)

    @chz.chz
    class Foo:
        a: int = 1
        b: int = 2

    partial_foo = functools.partial(Foo, a=3, b=4)

    assert chz.Blueprint(partial_foo).apply({"a": 5}).make() == Foo(a=5, b=4)

    @chz.chz
    class A:
        a: str = "a"

    @chz.chz
    class B(A):
        a: str = "b"

    @chz.chz
    class Main:
        a: A = chz.field(blueprint_unspecified=B)
        field: int = 0

    partial_main = functools.partial(Main, field=1)

    assert chz.Blueprint(partial_main).make() == Main(a=B(a="b"), field=1)


def test_blueprint_unspecified_functools_partial():
    @chz.chz
    class A:
        field: int
        typ: str = "a"

    @chz.chz
    class B(A):
        typ: str = "b"

    import functools

    @chz.chz
    class Main:
        a: A = chz.field(blueprint_unspecified=functools.partial(B, field=1))

    assert chz.Blueprint(Main).make() == Main(a=B(field=1))

    @chz.chz
    class C(A):
        missing: int

    @chz.chz
    class Main:
        a: A = chz.field(blueprint_unspecified=functools.partial(C, field=2))

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): a.missing"
    ):
        chz.Blueprint(Main).make()
