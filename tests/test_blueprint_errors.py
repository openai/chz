import pytest

import chz
from chz.blueprint import ConstructionException, ExtraneousBlueprintArg


def test_target_positional_only():
    def good(a: int = 42, /):
        return a

    assert chz.entrypoint(good, argv=[]) == 42

    def bad(a: int, /):
        return a

    with pytest.raises(
        ConstructionException,
        match="Cannot construct bad because it has positional-only parameter a without a default",
    ):
        chz.entrypoint(bad, argv=[])


def test_target_args_kwargs():
    def bad1(*args): ...

    with pytest.raises(
        ConstructionException,
        match=r"Cannot collect parameters from bad1 due to \*args parameter args",
    ):
        chz.entrypoint(bad1, argv=[])

    def bad2(**kwargs): ...

    with pytest.raises(
        ConstructionException,
        match=r"Cannot collect parameters from bad2 due to \*\*kwargs parameter kwargs",
    ):
        chz.entrypoint(bad2, argv=[])


def test_target_bad_signature():
    def bad(a: int, b: str): ...

    bad.__text_signature__ = "not a signature"

    with pytest.raises(ConstructionException, match=r"Failed to get signature for bad"):
        chz.entrypoint(bad, argv=[])


def test_target_just_plain_old_bad():
    with pytest.raises(ValueError, match="42 is not callable"):
        chz.entrypoint(42, argv=[])


def test_target_no_params_extraneous():
    def good(): ...

    with pytest.raises(
        ExtraneousBlueprintArg, match=r"Extraneous argument 'a' to Blueprint for .*\.good"
    ):
        chz.entrypoint(good, argv=["a=42"])


def test_nested_target_default_values():
    @chz.chz
    class Main:
        a: int

    def good(m: Main, b="asdf", c=1):
        return m.a

    assert chz.nested_entrypoint(good, argv=["a=42"]) == 42

    def bad(m: Main, b, c=1): ...

    with pytest.raises(
        ValueError,
        match=r"Nested entrypoints must take at most one argument without a default",
    ):
        chz.nested_entrypoint(bad, argv=["a=42"])


def test_blueprint_extraneous_valid_parent():
    @chz.chz
    class C:
        field: int

    @chz.chz
    class B:
        c: C

    @chz.chz
    class A:
        b: B

    with pytest.raises(
        ExtraneousBlueprintArg,
        match=r"""Extraneous argument 'b.cc.nope' to Blueprint for test_blueprint_errors:test_blueprint_extraneous_valid_parent.<locals>.A \(from command line\)
Param 'b' is closest valid ancestor
Append --help to your command to see valid arguments""",
    ):
        chz.entrypoint(A, argv=["b.cc.nope=0"])
