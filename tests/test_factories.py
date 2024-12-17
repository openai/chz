"""

Watch out for some of the extra parentheses in these tests.

"""

import typing

import pytest

from chz.factories import MetaFromString, standard


class A: ...


class B(A): ...


B_alias = B


class C(B): ...


class X: ...


def foo():
    return A()


bar = 0


a = A()


def test_standard_subclass():
    f = standard(annotation=A)

    assert f.unspecified_factory() is A

    assert f.from_string("A") is A
    assert f.from_string("B") is B
    assert f.from_string("C") is C

    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'X'"):
        f.from_string("X")
    with pytest.raises(
        MetaFromString,
        match="Expected test_factories:X from 'test_factories:X' to be a subtype of test_factories:A",
    ):
        f.from_string(f"{__name__}:X")

    assert f.from_string(f"{__name__}:A") is A
    assert f.from_string(f"{__name__}:B") is B
    assert f.from_string(f"{__name__}:C") is C

    assert f.from_string(f"{__name__}.A") is A
    assert f.from_string(f"{__name__}.B") is B
    assert f.from_string(f"{__name__}.C") is C


def test_standard_subclass_unspecified():
    f = standard(annotation=A, unspecified=B)

    assert f.unspecified_factory() is B

    assert f.from_string("A") is A
    assert f.from_string("B") is B
    assert f.from_string("C") is C

    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'X'"):
        f.from_string("X")

    assert f.from_string(f"{__name__}:A") is A
    assert f.from_string(f"{__name__}:B") is B
    assert f.from_string(f"{__name__}:C") is C


def test_standard_subclass_module():
    f = standard(annotation=A)
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'a'"):
        f.from_string("a")
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'foo'"):
        f.from_string("foo")
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'bar'"):
        f.from_string("bar")
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'X'"):
        f.from_string("X")
    assert f.from_string(f"{__name__}:a")() is a
    assert f.from_string(f"{__name__}:foo") is foo
    with pytest.raises(MetaFromString, match="Expected 0 from 'test_factories:bar' to be callable"):
        f.from_string(f"{__name__}:bar")

    f = standard(annotation=A, default_module=__name__)
    assert f.from_string("a")() is a
    assert f.from_string("foo") is foo
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'bar'"):
        assert f.from_string("bar") is foo
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'X'"):
        f.from_string("X")
    assert f.from_string(f"{__name__}:a")() is a
    assert f.from_string(f"{__name__}:foo") is foo
    with pytest.raises(MetaFromString, match="Expected 0 from 'test_factories:bar' to be callable"):
        f.from_string(f"{__name__}:bar")
    with pytest.raises(
        MetaFromString,
        match="Expected test_factories:X from 'test_factories:X' to be a subtype of test_factories:A",
    ):
        f.from_string(f"{__name__}:X")


def test_standard_subclass_object_any():
    import collections.abc

    for any_object in (object, typing.Any):
        f = standard(annotation=any_object)
        with pytest.raises(MetaFromString, match="Could not find 'a', try a fully qualified name"):
            f.from_string("a")
        with pytest.raises(
            MetaFromString, match="Could not find 'foo', try a fully qualified name"
        ):
            f.from_string("foo")
        assert f.from_string(f"{__name__}:a")() is a
        assert f.from_string(f"{__name__}:foo") is foo
        assert f.from_string(f"{__name__}:bar")() is bar

        f = standard(annotation=any_object, default_module=__name__)

        assert f.from_string("a")() is a
        assert f.from_string("foo") is foo
        assert f.from_string("bar")() is bar

        assert f.from_string("collections.abc.MutableSequence") is collections.abc.MutableSequence

        f = standard(annotation=any_object, unspecified=type[object])
        assert f.unspecified_factory() != type[object]
        assert f.unspecified_factory()() is object

        f = standard(annotation=any_object, unspecified=type)
        assert f.unspecified_factory() is type


def test_standard_type_subclass():
    f = standard(annotation=type[A])

    assert f.unspecified_factory()() is A

    assert f.from_string("A")() is A
    assert f.from_string("B")() is B
    assert f.from_string("C")() is C

    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'X'"):
        f.from_string("X")

    assert f.from_string(f"{__name__}:A")() is A
    assert f.from_string(f"{__name__}:B")() is B
    assert f.from_string(f"{__name__}:C")() is C


def test_standard_type_subclass_unspecified():
    f = standard(annotation=type[A], unspecified=type[B])

    assert f.unspecified_factory()() is B

    assert f.from_string("A")() is A
    assert f.from_string("B")() is B
    assert f.from_string("C")() is C

    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'X'"):
        f.from_string("X")

    assert f.from_string(f"{__name__}:A")() is A
    assert f.from_string(f"{__name__}:B")() is B
    assert f.from_string(f"{__name__}:C")() is C


def test_standard_type_subclass_module():
    f = standard(annotation=type[A])
    with pytest.raises(MetaFromString, match="No subclass of test_factories:A named 'B_alias'"):
        f.from_string("B_alias")
    assert f.from_string(f"{__name__}:B_alias")() is B

    f = standard(annotation=type[A], default_module=__name__)
    assert f.from_string("B_alias")() is B
    assert f.from_string(f"{__name__}:B_alias")() is B


def test_standard_union():
    f = standard(annotation=A | X)

    assert f.unspecified_factory() is None

    assert f.from_string("A") is A
    assert f.from_string("B") is B
    assert f.from_string("C") is C
    assert f.from_string("X") is X

    with pytest.raises(MetaFromString, match="Could not produce a union instance from 'object'"):
        f.from_string("object")

    assert f.from_string(f"{__name__}:A") is A
    assert f.from_string(f"{__name__}:B") is B
    assert f.from_string(f"{__name__}:C") is C
    assert f.from_string(f"{__name__}:X") is X


def test_standard_union_unspecified():
    f = standard(annotation=A | X, unspecified=B)

    assert f.unspecified_factory() is B

    assert f.from_string("A") is A
    assert f.from_string("B") is B
    assert f.from_string("C") is C
    assert f.from_string("X") is X

    with pytest.raises(MetaFromString, match="Could not produce a union instance from 'object'"):
        f.from_string("object")

    assert f.from_string(f"{__name__}:A") is A
    assert f.from_string(f"{__name__}:B") is B
    assert f.from_string(f"{__name__}:C") is C
    assert f.from_string(f"{__name__}:X") is X


def test_standard_union_optional():
    f = standard(annotation=A | None)

    assert f.unspecified_factory() is A

    assert f.from_string("A") is A
    assert f.from_string("None")() is None

    with pytest.raises(MetaFromString, match="Could not produce a union instance from 'object'"):
        f.from_string("object")

    f = standard(annotation=int | None)

    assert f.perform_cast("123") == 123
    assert f.perform_cast("None") is None


def test_standard_union_module():
    f = standard(annotation=A | X)
    with pytest.raises(MetaFromString, match="Could not produce a union instance from 'a'"):
        f.from_string("a")
    with pytest.raises(MetaFromString, match="Could not produce a union instance from 'foo'"):
        f.from_string("foo")
    assert f.from_string(f"{__name__}:a")() is a
    assert f.from_string(f"{__name__}:foo") is foo

    f = standard(annotation=A, default_module=__name__)
    assert f.from_string("a")() is a
    assert f.from_string("foo") is foo
    assert f.from_string(f"{__name__}:a")() is a
    assert f.from_string(f"{__name__}:foo") is foo


def test_standard_union_type():
    f = standard(annotation=type[A] | type[X])
    assert f.unspecified_factory() == None

    f = standard(annotation=type[A | X])
    assert f.unspecified_factory() == None

    f = standard(annotation=type[A] | type[X], unspecified=type[B])
    assert f.unspecified_factory() != type[B]
    assert f.unspecified_factory()() is B

    f = standard(annotation=type[A | X], unspecified=type[B])
    assert f.unspecified_factory() != type[B]
    assert f.unspecified_factory()() is B


def test_standard_type_generic():
    f = standard(annotation=type[list[int]])
    assert f.unspecified_factory() is not list
    assert f.unspecified_factory() != list[int]
    assert f.unspecified_factory()() == list[int]


def test_standard_lambda():
    f = standard(annotation=int)
    assert f.from_string("lambda: 123")() == 123
    assert f.from_string("lambda x, y: x + y")(1, 2) == 3


def test_standard_none():
    f = standard(annotation=None)
    assert f.unspecified_factory()() is None
    assert f.from_string("None")() is None


def test_standard_special_forms():
    f = standard(annotation=typing.Literal["foo", "bar"])
    assert f.unspecified_factory() is None

    with pytest.raises(
        MetaFromString, match=r"Could not produce a Literal\['foo', 'bar'\] instance from 'foo'"
    ):
        f.from_string("foo")
