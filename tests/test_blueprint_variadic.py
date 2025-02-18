import typing

import pytest

import chz
from chz.blueprint import (
    Castable,
    ConstructionException,
    ExtraneousBlueprintArg,
    InvalidBlueprintArg,
    MissingBlueprintArg,
)


def test_variadic_list():
    @chz.chz
    class X:
        a: int

    @chz.chz
    class MainList:
        xs: list[X]

    assert chz.Blueprint(MainList).apply({"xs.0.a": 1}).make() == MainList(xs=[X(a=1)])

    assert chz.Blueprint(MainList).apply(
        {"xs.0.a": 1, "xs.1.a": 2, "xs.2.a": 3}
    ).make() == MainList(xs=[X(a=1), X(a=2), X(a=3)])

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): xs"
    ):
        chz.Blueprint(MainList).make()

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): xs.1.a"
    ):
        chz.Blueprint(MainList).apply({"xs.0.a": 1, "xs.2.a": 3}).make()

    @chz.chz
    class MainListDefault:
        xs: list[X] = chz.field(default_factory=list)

    assert chz.Blueprint(MainListDefault).make() == MainListDefault(xs=[])


def test_variadic_wildcard():
    @chz.chz
    class X:
        a: int
        b: int

    @chz.chz
    class MainList:
        xs: list[X]

    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument '\.\.\.a'"):
        chz.Blueprint(MainList).apply({"...a": 1}).make()

    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument '\.\.\.0.a'"):
        chz.Blueprint(MainList).apply({"...0.a": 1}).make()

    assert chz.Blueprint(MainList).apply({"xs.0.a": 0, "...0.b": 1}).make() == MainList(
        xs=[X(a=0, b=1)]
    )

    assert chz.Blueprint(MainList).apply({"xs.0.a": 0, "...b": 1}).make() == MainList(
        xs=[X(a=0, b=1)]
    )

    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument '\.\.\.0.a'"):
        chz.Blueprint(MainList).apply({"...0.a": 0}).make()
    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument '\.\.\.0'"):
        chz.Blueprint(MainList).apply({"...0": 0}).make()

    assert chz.Blueprint(MainList).apply({"...xs.0.a": 0, "...xs.0.b": 0}).make() == MainList(
        xs=[X(a=0, b=0)]
    )

    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument 'xs\.\.\.a'"):
        chz.Blueprint(MainList).apply({"xs...a": 5}).make()


def test_variadic_tuple():
    @chz.chz
    class X:
        a: int

    @chz.chz
    class MainHomoTuple:
        xs: tuple[X, ...]

    assert chz.Blueprint(MainHomoTuple).apply(
        {"xs.0.a": 1, "xs.1.a": 2, "xs.2.a": 3}
    ).make() == MainHomoTuple(xs=(X(a=1), X(a=2), X(a=3)))

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): xs"
    ):
        chz.Blueprint(MainHomoTuple).make()

    with pytest.raises(
        MissingBlueprintArg, match=r"Missing required arguments for parameter\(s\): xs.1.a"
    ):
        chz.Blueprint(MainHomoTuple).apply({"xs.0.a": 1, "xs.2.a": 3}).make()

    @chz.chz
    class Y:
        b: str

    @chz.chz
    class MainHeteroTuple:
        xs: tuple[X, Y, X]

    assert chz.Blueprint(MainHeteroTuple).apply(
        {"xs.0.a": 1, "xs.1.b": "str", "xs.2.a": 3}
    ).make() == MainHeteroTuple(xs=(X(a=1), Y(b="str"), X(a=3)))

    with pytest.raises(
        TypeError,
        match=r"Tuple type tuple\[.*X.*Y.*X\] for 'xs' must take 3 items; arguments for index 9 were specified",
    ):
        chz.Blueprint(MainHeteroTuple).apply({"xs.0.a": 1, "xs.9.b": "str"}).make()

    with pytest.raises(ExtraneousBlueprintArg, match=r"Extraneous argument 'xs.1.a'"):
        chz.Blueprint(MainHeteroTuple).apply({"xs.0.a": 1, "xs.1.a": 2, "xs.2.a": 3}).make()


def test_variadic_dict():
    @chz.chz
    class X:
        a: int

    @chz.chz
    class MainDict:
        xs: dict[str, X]

    assert chz.Blueprint(MainDict).apply(
        {"xs.first.a": 1, "xs.second.a": 2, "xs.3.a": 3}
    ).make() == MainDict(xs={"first": X(a=1), "second": X(a=2), "3": X(a=3)})


def test_variadic_collections_type():
    @chz.chz
    class X:
        a: int

    @chz.chz
    class Main:
        seq: typing.Sequence[X]
        map: typing.Mapping[str, X]

    assert chz.Blueprint(Main).apply(
        {"seq.0.a": 1, "seq.1.a": 2, "map.first.a": 3, "map.second.a": 4}
    ).make() == Main(seq=(X(a=1), X(a=2)), map={"first": X(a=3), "second": X(a=4)})


def test_variadic_dict_non_str_key():
    @chz.chz
    class MainDict:
        xs: dict[int, str]

    with pytest.raises(TypeError, match="Variadic dict type must take str keys, not int"):
        chz.Blueprint(MainDict).apply({"xs.0": "a", "xs.1": "2"}).make()

    assert chz.Blueprint(MainDict).apply({"xs": {1: "2"}}).make() == MainDict(xs={1: "2"})

    @chz.chz
    class MainDict2:
        xs: dict[int, str] | None = None

    assert chz.Blueprint(MainDict2).make() == MainDict2(xs=None)


def test_variadic_dict_unannotated():
    @chz.chz
    class MainDict:
        xs: dict

    assert chz.Blueprint(MainDict).apply({"xs.0": "a", "xs.first": 123}).make() == MainDict(
        xs={"0": "a", "first": 123}
    )


def test_variadic_typed_dict():
    class Foo(typing.TypedDict):
        bar: int
        baz: str

    @chz.chz(typecheck=True)
    class Main:
        foo: Foo

    assert chz.Blueprint(Main).apply(
        {"foo.bar": Castable("3"), "foo.baz": Castable("43")}
    ).make() == Main(foo={"bar": 3, "baz": "43"})

    with pytest.raises(
        ExtraneousBlueprintArg, match=r"Extraneous argument 'foo.typo' to Blueprint for .*Main"
    ):
        chz.Blueprint(Main).apply({"foo.bar": 3, "foo.typo": "baz"}).make()

    with pytest.raises(TypeError, match=r"Expected 'foo.bar' to be int, got str"):
        chz.Blueprint(Main).apply({"foo.bar": "bar", "foo.baz": "baz"}).make()

    with pytest.raises(
        InvalidBlueprintArg,
        match=(
            "Could not interpret argument 'bar' provided for param 'foo.bar'...\n\n"
            "- Failed to interpret it as a value:\n"
            "Could not cast 'bar' to int"
        ),
    ):
        chz.Blueprint(Main).apply({"foo.bar": Castable("bar"), "foo.baz": "baz"}).make()


def test_variadic_typed_dict_not_required():
    class Foo(typing.TypedDict):
        a: int
        b: typing.Required[int]
        c: typing.NotRequired[int]

    class Bar(Foo, total=False):
        d: int
        e: typing.Required[int]
        f: typing.NotRequired[int]

    class Baz(Bar):
        g: int
        h: typing.Required[int]
        i: typing.NotRequired[int]

    @chz.chz
    class Main:
        foo: Foo
        bar: Bar
        baz: Baz

    assert chz.Blueprint(Main).apply(
        {
            "foo.a": Castable("1"),
            "foo.b": Castable("2"),
            "foo.c": Castable("3"),
            "bar.a": Castable("4"),
            "bar.b": Castable("5"),
            "bar.c": Castable("6"),
            "bar.d": Castable("7"),
            "bar.e": Castable("8"),
            "bar.f": Castable("9"),
            "baz.a": Castable("10"),
            "baz.b": Castable("11"),
            "baz.c": Castable("12"),
            "baz.d": Castable("13"),
            "baz.e": Castable("14"),
            "baz.f": Castable("15"),
            "baz.g": Castable("16"),
            "baz.h": Castable("17"),
            "baz.i": Castable("18"),
        }
    ).make() == Main(
        foo={"a": 1, "b": 2, "c": 3},
        bar={"a": 4, "b": 5, "c": 6, "d": 7, "e": 8, "f": 9},
        baz={"a": 10, "b": 11, "c": 12, "d": 13, "e": 14, "f": 15, "g": 16, "h": 17, "i": 18},
    )

    # Test that c, d, f, i are not required
    assert chz.Blueprint(Main).apply(
        {
            "foo.a": Castable("1"),
            "foo.b": Castable("2"),
            "bar.a": Castable("3"),
            "bar.b": Castable("4"),
            "bar.e": Castable("5"),
            "baz.a": Castable("6"),
            "baz.b": Castable("7"),
            "baz.e": Castable("8"),
            "baz.g": Castable("9"),
            "baz.h": Castable("10"),
        }
    ).make() == Main(
        foo={"a": 1, "b": 2},
        bar={"a": 3, "b": 4, "e": 5},
        baz={"a": 6, "b": 7, "e": 8, "g": 9, "h": 10},
    )

    # Test that a, b, e, g, h are required
    with pytest.raises(
        MissingBlueprintArg,
        match=(
            r"Missing required arguments for parameter\(s\): "
            r"foo.a, foo.b, bar.a, bar.b, bar.e, baz.a, baz.b, baz.e, baz.g, baz.h"
        ),
    ):
        chz.Blueprint(Main).make()

    print(chz.Blueprint(Main).get_help())
    assert (
        chz.Blueprint(Main).get_help()
        == """WARNING: Missing required arguments for parameter(s): foo.a, foo.b, bar.a, bar.b, bar.e, baz.a, baz.b, baz.e, baz.g, baz.h

Entry point: test_blueprint_variadic:test_variadic_typed_dict_not_required.<locals>.Main

Arguments:
  foo    test_blueprint_variadic:test_variadic_typed_dict_not_required.<locals>.Foo        -
  foo.a  int                                       -
  foo.b  int                                       -
  foo.c  int                                       typing.NotRequired (default)
  bar    test_blueprint_variadic:test_variadic_typed_dict_not_required.<locals>.Bar        -
  bar.a  int                                       -
  bar.b  int                                       -
  bar.c  int                                       typing.NotRequired (default)
  bar.d  int                                       typing.NotRequired (default)
  bar.e  int                                       -
  bar.f  int                                       typing.NotRequired (default)
  baz    test_blueprint_variadic:test_variadic_typed_dict_not_required.<locals>.Baz        -
  baz.a  int                                       -
  baz.b  int                                       -
  baz.c  int                                       typing.NotRequired (default)
  baz.d  int                                       typing.NotRequired (default)
  baz.e  int                                       -
  baz.f  int                                       typing.NotRequired (default)
  baz.g  int                                       -
  baz.h  int                                       -
  baz.i  int                                       typing.NotRequired (default)
"""
    )


def test_variadic_default():
    @chz.chz
    class X:
        a: int = 0

    @chz.chz
    class MainList:
        xs: list[X]

    assert chz.Blueprint(MainList).apply({"xs.3.a": 5}).make() == MainList(
        xs=[X(a=0), X(a=0), X(a=0), X(a=5)]
    )


def test_variadic_default_wildcard_error():
    @chz.chz
    class X:
        a: int

    @chz.chz
    class MainList:
        xs: list[X] = chz.field(default_factory=lambda: [X(a=0)])
        a: int  # same name as X.a, to prevent unused wildcard error

    with pytest.raises(
        ConstructionException,
        match=(
            r'The parameter "xs" is variadic(.|\n)*'
            r'However, you also specified the wildcard "\.\.\.a" and you may '
            r'have expected it to modify the value of "xs\.\(variadic\)\.a"'
        ),
    ):
        chz.Blueprint(MainList).apply({"...a": 1}).make()

    @chz.chz
    class MainListOk:
        xs: list[X] = chz.field(default_factory=list)
        a: int  # same name as X.a, to prevent unused wildcard error

    assert chz.Blueprint(MainListOk).apply({"...a": 1}).make() == MainListOk(xs=[], a=1)


def test_variadic_default_wildcard_error_using_types_from_default():
    @chz.chz
    class Clause:
        def value(self) -> bool:
            raise NotImplementedError

    @chz.chz
    class SimpleClause(Clause):
        val: bool

        def value(self) -> bool:
            return self.val

    @chz.chz
    class FalseClause(SimpleClause):
        val: bool = False

    @chz.chz
    class AndClause(Clause):
        clauses: tuple[Clause, ...] = ()

        def value(self) -> bool:
            return all(clause.value() for clause in self.clauses)

    @chz.chz
    class MyClause(AndClause):
        # Need to check both Clause and FalseClause for wildcard matches
        clauses: tuple[Clause, ...] = (FalseClause(), FalseClause())

    with pytest.raises(
        ConstructionException,
        match=(
            r'The parameter "clauses.1.clauses" is variadic(.|\n)*'
            r'However, you also specified the wildcard "\.\.\.val" and you may '
            r'have expected it to modify the value of "clauses.1.clauses\.\(variadic\)\.val"'
        ),
    ):
        chz.Blueprint(AndClause).apply_from_argv(
            ["clauses.0=SimpleClause", "clauses.1=MyClause", "...val=True"]
        ).make()


def test_polymorphic_variadic_generic():
    @chz.chz
    class A:
        a: int

    @chz.chz
    class AA(A): ...

    @chz.chz
    class MainList:
        xs: list[A]

    assert chz.Blueprint(MainList).apply(
        {"xs": Castable("list[AA]"), "xs.0.a": 1}
    ).make() == MainList(xs=[AA(a=1)])

    @chz.chz
    class MainTuple:
        xs: tuple[A, ...]

    assert chz.Blueprint(MainTuple).apply(
        {"xs": Castable("tuple[AA, ...]"), "xs.0.a": 1}
    ).make() == MainTuple(xs=(AA(a=1),))

    @chz.chz
    class MainListList:
        xs: list[list[A]]

    # This is gtting a little silly :-)
    assert chz.Blueprint(MainListList).apply(
        {"xs": Castable("list[list[AA]]"), "xs.0.0.a": 1}
    ).make() == MainListList(xs=[[AA(a=1)]])
