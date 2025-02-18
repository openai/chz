import math
import re
from typing import Generic, TypeVar

import pytest

import chz

T = TypeVar("T")


def test_validate_readme():
    @chz.chz
    class Fraction:
        numerator: int = chz.field(validator=chz.validators.typecheck)
        denominator: int = chz.field(validator=[chz.validators.typecheck, chz.validators.gt(0)])

        @chz.validate
        def _check_reduced(self):
            if math.gcd(self.numerator, self.denominator) > 1:
                raise ValueError("Fraction is not reduced")

    Fraction(numerator=1, denominator=2)
    Fraction(numerator=2, denominator=1)
    with pytest.raises(ValueError, match=r"Fraction is not reduced"):
        Fraction(numerator=2, denominator=4)


def test_validate():
    @chz.chz
    class X:
        attr: int = chz.field(validator=chz.validators.instancecheck)

    X(attr=1)
    with pytest.raises(TypeError, match="Expected X_attr to be int, got str"):
        X(attr="1")  # type: ignore

    @chz.chz
    class Y:
        attr: int = chz.field(validator=chz.validators.instance_of(int))

        @chz.validate
        def _attr_validator(self):
            if self.attr < 0:
                raise ValueError("attr must be non-negative")

    Y(attr=1)
    with pytest.raises(TypeError, match="Expected X_attr to be int, got str"):
        Y(attr="1")  # type: ignore
    with pytest.raises(ValueError, match="attr must be non-negative"):
        Y(attr=-1)

    @chz.chz
    class Z:
        attr: int | str = chz.field(validator=chz.validators.typecheck)

    Z(attr=1)
    Z(attr="asdf")
    with pytest.raises(TypeError, match=r"int \| str, got bytes"):
        Z(attr=b"fdsa")  # type: ignore


def test_validate_replace():
    @chz.chz
    class X:
        attr: int = chz.field(validator=chz.validators.typecheck)

    x = X(attr=1)
    x = chz.replace(x, attr=2)
    with pytest.raises(TypeError, match="Expected X_attr to be int, got str"):
        chz.replace(x, attr="3")


def test_for_all_fields():
    @chz.chz
    class X:
        a: str
        b: int

        @chz.validate
        def typecheck_all_fields(self):
            chz.validators.for_all_fields(chz.validators.typecheck)(self)

    X(a="asdf", b=1)
    with pytest.raises(TypeError, match="Expected X_a to be str, got int"):
        X(a=1, b=1)
    with pytest.raises(TypeError, match="Expected X_b to be int, got str"):
        X(a="asdf", b="asdf")
    with pytest.raises(TypeError, match="Expected X_a to be str, got int"):
        X(a=1, b="asdf")


def test_validate_inheritance_field_level():
    @chz.chz
    class X:
        a: str = chz.field(validator=chz.validators.typecheck)

    @chz.chz
    class Y(X):
        b: int

    with pytest.raises(TypeError, match="Expected X_a to be str, got int"):
        Y(a=1, b=1)

    @chz.chz
    class A:
        x: X = chz.field(validator=chz.validators.typecheck)

    @chz.chz
    class B(A):
        x: Y

    A(x=X(a="asdf"))
    A(x=Y(a="asdf", b=1))
    B(x=Y(a="asdf", b=1))
    # But note that if you clobber an attribute, the field-level validator also gets clobbered
    B(x=X(a="asdf"))


def test_validate_init_property():
    @chz.chz
    class A1:
        X_attr: str = chz.field(validator=chz.validators.instancecheck)

        @chz.init_property
        def attr(self) -> str:
            return str(self.X_attr)

    A1(attr="attr")
    with pytest.raises(TypeError, match="Expected X_attr to be str, got int"):
        A1(attr=1)

    @chz.chz
    class A2:
        X_attr: int = chz.field(validator=chz.validators.instancecheck)

        @chz.init_property
        def attr(self) -> str:  # changes type
            return str(self.X_attr)

    A2(attr=1)

    with pytest.raises(TypeError, match="Expected X_attr to be int, got str"):
        A2(attr="attr")


def test_validate_init_property_order():
    @chz.chz
    class A:
        value: int = chz.field(validator=chz.validators.gt(0))

        @chz.init_property
        def reciprocal(self):
            return 1 / self.value

    with pytest.raises(ValueError, match="Expected X_value to be greater than 0, got 0"):
        A(value=0)


def test_validate_munger():
    # See comments in __chz_validate__

    @chz.chz
    class A:
        a: int = chz.field(munger=lambda s, v: 100, validator=chz.validators.gt(10))

    with pytest.raises(ValueError, match="Expected X_a to be greater than 10, got 1"):
        A(a=1)

    @chz.chz
    class A:
        a: int = chz.field(munger=lambda s, v: 100, validator=chz.validators.lt(10))

    with pytest.raises(ValueError, match="Expected a to be less than 10, got 100"):
        A(a=1)


def test_validate_inheritance_class_level():
    @chz.chz
    class X:
        a: str

        @chz.validate
        def check_a_is_banana(self):
            if self.a != "banana":
                raise ValueError("Banana only")

    @chz.chz
    class Y(X):
        b: int

    with pytest.raises(ValueError, match="Banana only"):
        Y(a="nana", b=1)

    @chz.chz
    class Z(Y):
        c: bytes

        @chz.validate
        def check_c_is_not_empty(self):
            if not self.c:
                raise ValueError("c must not be empty")

        @chz.validate
        def check_b_is_positive(self):
            if self.b < 0:
                raise ValueError("b must be positive")

    X(a="banana")
    Y(a="banana", b=1)
    Y(a="banana", b=-1)

    with pytest.raises(ValueError, match="Banana only"):
        Z(a="nana", b=1, c=b"asdf")
    with pytest.raises(ValueError, match="b must be positive"):
        Z(a="banana", b=-1, c=b"asdf")

    Z(a="banana", b=1, c=b"asdf")

    assert len(X.__chz_validators__) == 1
    assert len(Y.__chz_validators__) == 1
    assert len(Z.__chz_validators__) == 3


def test_validate_decorator_option():
    @chz.chz(typecheck=True)
    class X:
        a: str

    X(a="asdf")
    with pytest.raises(TypeError, match="Expected X_a to be str, got int"):
        X(a=1)

    @chz.chz
    class Y(X):
        b: int

    Y(a="asdf", b=1)
    with pytest.raises(TypeError, match="Expected X_a to be str, got int"):
        Y(a=1, b=1)
    with pytest.raises(TypeError, match="Expected X_b to be int, got str"):
        Y(a="asdf", b="asdf")

    @chz.chz(typecheck=True)
    class Z(X):
        c: bytes

    assert len(Z.__chz_validators__) == 1

    with pytest.raises(ValueError, match="Cannot disable typecheck; all validators are inherited"):

        @chz.chz(typecheck=False)
        class A(X):
            pass


def test_validate_mixins():
    results = set()

    @chz.chz
    class M1:
        @chz.validate
        def v1(self):
            results.add("v1")

    class M2NonChz:
        @chz.validate
        def v2(self):
            results.add("v2")

    @chz.chz
    class M3:
        @chz.validate
        def v3(self):
            results.add("v3")

    @chz.chz
    class Main(M1, M2NonChz, M3):
        @chz.validate
        def v4(self):
            results.add("v4")

    Main()
    assert results == {"v1", "v2", "v3", "v4"}


def test_validate_valid_regex():
    @chz.chz
    class A:
        attr: str = chz.field(validator=chz.validators.valid_regex)

    A(attr=".*")
    with pytest.raises(
        ValueError, match="Invalid regex in X_attr: nothing to repeat at position 0"
    ):
        A(attr="*")


def test_validate_literal():
    from typing import Literal

    @chz.chz(typecheck=True)
    class A:
        attr: Literal["a", "b"]

    A(attr="a")
    A(attr="b")
    with pytest.raises(TypeError, match=r"Expected X_attr to be Literal\['a', 'b'\], got 'c'"):
        A(attr="c")


def test_validate_const_default():
    @chz.chz
    class Image:
        encoding: str

    @chz.chz
    class PNG(Image):
        encoding: str = chz.field(default="png", validator=chz.validators.const_default)

    PNG()
    PNG(encoding="png")
    with pytest.raises(
        ValueError, match="Expected X_encoding to match the default 'png', got 'jpg'"
    ):
        PNG(encoding="jpg")


def test_validate_field_consistency():
    @chz.chz
    class D:
        const: int

    @chz.chz
    class C:
        map: dict[str, D]
        seq: list[D]

    @chz.chz
    class B:
        const: int
        c: C

    @chz.chz
    class A:
        const: int
        b: B

        @chz.validate
        def field_consistency(self):
            chz.validators.check_field_consistency_in_tree(self, {"const"})

    with pytest.raises(
        ValueError,
        match=re.escape(
            """\
Field 'const' has inconsistent values in object tree:
1 at const
2 at b.const
3 at b.c.map.a.const
4 at b.c.seq.0.const, b.c.seq.1.const, b.c.seq.2.const, ... (1 more)"""
        ),
    ):
        A(
            const=1,
            b=B(
                const=2,
                c=C(map={"a": D(const=3)}, seq=[D(const=4), D(const=4), D(const=4), D(const=4)]),
            ),
        )

    @chz.chz
    class F:
        const: int

    @chz.chz
    class E:
        seq: list[F]

    @chz.chz
    class D:
        const: int
        e: E

        @chz.validate
        def field_consistency(self):
            chz.validators.check_field_consistency_in_tree(self, {"const"}, regex_root=r"e\.seq")

    # This should not raise an error because the check is only done on the `e.seq` field
    assert D(const=1, e=E(seq=[F(const=3), F(const=3)])).e.seq[0].const == 3

    with pytest.raises(
        ValueError,
        match=re.escape(
            """\
Field 'const' has inconsistent values in object tree:
3 at e.seq.0.const
4 at e.seq.1.const"""
        ),
    ):
        D(const=1, e=E(seq=[F(const=3), F(const=4)]))


def test_is_override_catches_non_overriding() -> None:
    @chz.chz
    class HasBase:
        x_different_name: int = 0

    @chz.chz
    class MyHasBase(HasBase):
        x: int = chz.field(default=1, validator=chz.validators.is_override)

    with pytest.raises(
        ValueError,
        match="Field x does not exist in any parent classes of test_validate:.*MyHasBase",
    ):
        MyHasBase()


def test_is_override_catches_bad_types() -> None:
    @chz.chz
    class Base:
        x: int = 1
        my_tuple: tuple[int, str] = (0, "good")
        my_homogenous_tuple: tuple[int, ...] = (0, 1)
        my_dict: dict[int, str] = chz.field(default_factory=lambda: {0: "hi"})

    Base()  # OK

    @chz.chz
    class GoodOverride(Base):
        x: int = chz.field(default=5, validator=chz.validators.is_override)
        my_tuple: tuple[int, str] = chz.field(
            default=(1, "hi"), validator=chz.validators.is_override
        )
        my_homogenous_tuple: tuple[int, ...] = chz.field(
            default=(1, 2), validator=chz.validators.is_override
        )
        my_dict: dict[int, str] = chz.field(
            default_factory=lambda: {0: "hi"}, validator=chz.validators.is_override
        )

    result = GoodOverride()
    assert result.x == 5
    assert result.my_tuple == (1, "hi")
    assert result.my_homogenous_tuple == (1, 2)
    assert result.my_dict == {0: "hi"}

    @chz.chz
    class BadInt(Base):
        x: int = chz.field(default="oops", validator=chz.validators.is_override)

    @chz.chz
    class BadTuple(Base):
        my_tuple: tuple[int, str] = chz.field(default=(1, 0), validator=chz.validators.is_override)

    @chz.chz
    class BadHomogenousTuple(Base):
        my_homogenous_tuple: tuple[int, ...] = chz.field(
            default=(1, "oops"), validator=chz.validators.is_override
        )

    @chz.chz
    class BadDict(Base):
        my_dict: dict[int, str] = chz.field(
            default_factory=lambda: {"oops": "foo"}, validator=chz.validators.is_override
        )

    for cls in [BadInt, BadTuple, BadHomogenousTuple, BadDict]:
        with pytest.raises(
            ValueError,
            match=r"test_validate:.*Bad.+\.X_.+' must be an instance of .+? to match the type on the original definition in test_validate:.*Base",
        ):
            cls()


def test_is_override_mixin_catches_bad_types() -> None:
    @chz.chz
    class Base:
        x: int = 1
        my_tuple: tuple[int, str] = (0, "good")
        my_homogenous_tuple: tuple[int, ...] = (0, 1)
        my_dict: dict[int, str] = chz.field(default_factory=lambda: {0: "hi"})

    Base()  # OK

    @chz.chz
    class GoodOverride(Base, chz.validators.IsOverrideMixin):
        x: int = chz.field(default=5)
        my_tuple: tuple[int, str] = chz.field(default=(1, "hi"))
        my_homogenous_tuple: tuple[int, ...] = chz.field(default=(1, 2))
        my_dict: dict[int, str] = chz.field(default_factory=lambda: {0: "hi"})

    result = GoodOverride()
    assert result.x == 5
    assert result.my_tuple == (1, "hi")
    assert result.my_homogenous_tuple == (1, 2)
    assert result.my_dict == {0: "hi"}

    @chz.chz
    class BadInt(Base, chz.validators.IsOverrideMixin):
        x: int = chz.field(default="oops")

    @chz.chz
    class BadTuple(Base, chz.validators.IsOverrideMixin):
        my_tuple: tuple[int, str] = chz.field(default=(1, 0))

    @chz.chz
    class BadHomogenousTuple(Base, chz.validators.IsOverrideMixin):
        my_homogenous_tuple: tuple[int, ...] = chz.field(default=(1, "oops"))

    @chz.chz
    class BadDict(Base, chz.validators.IsOverrideMixin):
        my_dict: dict[int, str] = chz.field(default_factory=lambda: {"oops": "foo"})

    for cls in [BadInt, BadTuple, BadHomogenousTuple, BadDict]:
        with pytest.raises(
            ValueError,
            match=r"test_validate:.*Bad.+\.X_.+' must be an instance of .+? to match the type on the original definition in test_validate:.*Base",
        ):
            cls()


def test_is_override_catches_bad_generic_default_factory() -> None:
    class Box(Generic[T]):
        def __init__(self, value: T):
            self.value = value

    @chz.chz
    class Atom(Generic[T]):
        box: Box[str]

    # Check that normal overriding words
    @chz.chz
    class MyGoodAtom(Atom, Generic[T]):
        box: Box[str] = chz.field(
            default_factory=lambda: Box[str]("hi"), validator=chz.validators.is_override
        )

    assert MyGoodAtom().box.value == "hi"

    @chz.chz
    class MyBadAtom(Atom, Generic[T]):
        box: Box[str] = chz.field(
            default_factory=lambda: Box[int](5), validator=chz.validators.is_override
        )

    with pytest.raises(
        ValueError,
        match=r"test_validate:.*MyBadAtom.X_box' must be an instance of .*Box\[str\] to match the type on the original definition in test_validate:.*\.Atom",
    ):
        MyBadAtom()


def test_is_override_works_with_default_factory() -> None:
    class Base:
        def __init__(self) -> None:
            self.value = 1

    @chz.chz
    class HasBases:
        bases: tuple[Base, ...]

    def my_bad_factory() -> tuple[Base, ...]:
        return Base(), "oop", Base()  # type: ignore

    @chz.chz
    class MyBadHasBases(HasBases):
        bases: tuple[Base, ...] = chz.field(
            default_factory=my_bad_factory, validator=chz.validators.is_override
        )

    with pytest.raises(
        ValueError,
        match=r".*MyBadHasBases.X_bases' must be an instance of tuple\[.*Base, \.\.\.\] to match the type on the original definition in .*\.HasBases",
    ):
        MyBadHasBases()


def test_is_override_mixin_catches_bad_types_in_subclasses() -> None:
    @chz.chz
    class Atom:
        x: int = 1

    @chz.chz
    class MyBadAtom(Atom, chz.validators.IsOverrideMixin):
        x: int = chz.field(default="foo")

    @chz.chz
    class Container:
        atom: Atom

    @chz.chz
    class MyBadContainer(Container):
        atom: Atom = chz.field(default_factory=MyBadAtom, blueprint_unspecified=MyBadAtom)

    with pytest.raises(
        ValueError,
        match=".*MyBadAtom.X_x' must be an instance of int to match the type on the original definition in .*Atom",
    ):
        MyBadContainer()
    with pytest.raises(
        ValueError,
        match=".*MyBadAtom.X_x' must be an instance of int to match the type on the original definition in .*Atom",
    ):
        chz.Blueprint(MyBadContainer).make()


def test_is_override_mixin_works_on_field_default() -> None:
    @chz.chz
    class Base:
        x: int = 1

    @chz.chz
    class BaseSub(Base, chz.validators.IsOverrideMixin):
        x: int = "foo"  # type: ignore  # that's the point of this test!

    with pytest.raises(
        ValueError,
        match=".*BaseSub.X_x' must be an instance of int to match the type on the original definition in .*Base",
    ):
        BaseSub()

    @chz.chz
    class BadIntermediate(Base):
        x: str = "sneaky intermediate class trying to mess things up"  # type: ignore

    @chz.chz
    class BadFinal(BadIntermediate, chz.validators.IsOverrideMixin):
        pass

    with pytest.raises(
        ValueError,
        match=".*BadFinal.X_x' must be an instance of int to match the type on the original definition in .*Base",
    ):
        BadFinal()

    @chz.chz
    class BadFinalThatMatchesIntermediate(BadIntermediate, chz.validators.IsOverrideMixin):
        x: str = "strings are bad here because it doesn't match the Base definition!"  # type: ignore

    with pytest.raises(
        ValueError,
        match=".*BadFinalThatMatchesIntermediate.X_x' must be an instance of int to match the type on the original definition in .*Base",
    ):
        BadFinalThatMatchesIntermediate()


def test_is_override_mixin_works_with_x_fields() -> None:
    @chz.chz
    class Base:
        X_value: str = "foo"

        @chz.init_property
        def value(self) -> tuple[str, ...]:
            return tuple(self.X_value.split(","))

    @chz.chz
    class SomeOverride(Base, chz.validators.IsOverrideMixin):
        X_value: str = chz.field(default="a,b")

    instance = chz.Blueprint(SomeOverride).make()
    assert instance.value == ("a", "b")

    @chz.chz
    class BadOverride(Base, chz.validators.IsOverrideMixin):
        X_value: tuple[str, ...] = chz.field(
            default=("look at me eagerly create", "a tuple of strings")
        )  # type: ignore

    @chz.chz
    class BadOverride2(Base, chz.validators.IsOverrideMixin):
        X_value: str = chz.field(default=("type signature is good", "but default is bad"))

    with pytest.raises(
        ValueError,
        match=r".*BadOverride.X_value' must be an instance of str to match the type on the original definition in .*Base",
    ):
        BadOverride()
    with pytest.raises(
        ValueError,
        match=r".*BadOverride2.X_value' must be an instance of str to match the type on the original definition in .*Base",
    ):
        BadOverride2()
