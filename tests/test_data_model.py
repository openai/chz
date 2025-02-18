# ruff: noqa: F811
import dataclasses
import functools
import json
import re
import typing

import pytest

import chz


def test_basic():
    @chz.chz
    class X:
        a: int

    @chz.chz()
    class Y:
        a: int = 3

    assert X(a=1).a == 1
    assert Y().a == 3

    assert chz.is_chz(X)
    assert chz.is_chz(X(a=1))
    assert not chz.is_chz(1)


with_future_annotation = """
from __future__ import annotations
try:
    class _test:
        _: _test
except NameError:
    raise AssertionError("from __future__ import annotations should be imported") from None
"""

without_future_annotation = """
try:
    class _test:
        _: _test
except NameError:
    pass
else:
    raise AssertionError("from __future__ import annotations should not be imported")
"""

basic_definition = """
@chz.chz
class X:
    a: int
    b: int = chz.field()
    c: str = "yikes"
    d: str = chz.field(default="yonks")
    e: str = chz.field(default_factory=lambda: "zeiks")
"""


def _test_construct_helper(X):
    with pytest.raises(TypeError, match="missing 2 required keyword-only arguments: 'a' and 'b'"):
        X()

    with pytest.raises(TypeError, match="missing 2 required keyword-only arguments: 'a' and 'b'"):
        X(1, 2)

    with pytest.raises(TypeError, match="missing 2 required keyword-only arguments: 'a' and 'b'"):
        X(c="okay")

    x = X(a=1, b=2)
    assert x.a == 1
    assert x.b == 2
    assert x.c == "yikes"
    assert x.d == "yonks"
    assert x.e == "zeiks"

    x = X(a=3, b=4, c="hijinks", d="iflunks", e="jourks")
    assert x.a == 3
    assert x.b == 4
    assert x.c == "hijinks"
    assert x.d == "iflunks"
    assert x.e == "jourks"


def test_construct_without_future_annotations():
    prog = without_future_annotation + basic_definition
    ns = {}
    exec(compile(prog, "", "exec", dont_inherit=True), {"chz": chz}, ns)
    X = ns["X"]
    _test_construct_helper(X)


def test_construct_with_future_annotations():
    prog = with_future_annotation + basic_definition
    ns = {}
    exec(compile(prog, "", "exec", dont_inherit=True), {"chz": chz}, ns)
    X = ns["X"]
    _test_construct_helper(X)


def test_inheritance():
    @chz.chz
    class X:
        a: int
        b: str
        c: str = chz.field(default="yikes")

    @chz.chz
    class Y(X):
        d: int
        e: str = chz.field(default="yonks")

    value = Y(a=1, b="2", d=3)
    assert value.a == 1
    assert value.b == "2"
    assert value.c == "yikes"
    assert value.d == 3
    assert value.e == "yonks"

    value = Y(a=1, b="2", d=3, e="4")
    assert value.a == 1
    assert value.b == "2"
    assert value.c == "yikes"
    assert value.d == 3
    assert value.e == "4"

    with pytest.raises(TypeError, match="missing 1 required keyword-only argument: 'd'"):
        Y(a=1, b="2")  # type: ignore

    with pytest.raises(
        ValueError,
        match="Cannot override field 'c' with a non-field member; maybe you're missing a type annotation?",
    ):

        @chz.chz
        class Z(X):
            c = "asdf"

    class NonChz(X):
        pass

    with pytest.raises(TypeError, match="NonChz is not decorated with @chz.chz"):
        NonChz(a=1, b="2", c="3")


def test_immutability():
    @chz.chz
    class X:
        a: int

    x = X(a=1)
    with pytest.raises(chz.data_model.FrozenInstanceError):
        x.a = 2  # type: ignore
    with pytest.raises(chz.data_model.FrozenInstanceError):
        x.b = 1  # type: ignore

    @chz.chz
    class Y:
        a: int

        @functools.cached_property
        def b(self):
            return self.a

        @property
        def c(self):
            return self.a

        @c.setter
        def c(self, value):
            self.a = value  # type: ignore

        @chz.init_property
        def d(self):
            return self.a

    y = Y(a=1)

    assert y.b == 1
    with pytest.raises(chz.data_model.FrozenInstanceError):
        y.b = 2  # type: ignore

    assert y.c == 1
    with pytest.raises(chz.data_model.FrozenInstanceError):
        y.c = 2  # type: ignore
    with pytest.raises(chz.data_model.FrozenInstanceError):
        del y.c  # type: ignore

    assert y.d == 1
    with pytest.raises(chz.data_model.FrozenInstanceError):
        y.d = 2  # type: ignore

    # Here's the loophole
    object.__setattr__(y, "a", 2)
    assert y.a == 2
    assert y.b == 1
    assert y.c == 2


def test_no_post_init():
    with pytest.raises(ValueError, match="Cannot define __post_init__"):

        @chz.chz
        class X:
            a: int

            def __post_init__(self):
                pass


def test_no_annotation():
    @chz.chz
    class X:
        a = 1

    X()
    with pytest.raises(TypeError, match=r"__init__\(\) got an unexpected keyword argument 'a'"):
        X(a=11)


def test_asdict():
    @chz.chz
    class Y:
        x: int
        y: bool

    @chz.chz
    class X:
        a: int
        b: str
        c: Y
        d: dict[str, bool]
        e: list[float]
        f: tuple[int, ...]

    x = X(a=1, b="2", c=Y(x=3, y=True), d={"a": True}, e=[1.0, 2.0], f=(1, 2))

    assert chz.asdict(x) == {
        "a": 1,
        "b": "2",
        "c": {"x": 3, "y": True},
        "d": {"a": True},
        "e": [1.0, 2.0],
        "f": (1, 2),
    }


def test_asdict_computed_properties():
    @chz.chz
    class C:
        x: float

        @property
        def doubled(self):
            return self.x * 2

        @functools.cached_property
        def tripled(self):
            return self.x * 3

        @chz.init_property
        def quadrupled(self):
            return self.x * 4

    c = C(x=1.0)
    assert chz.asdict(c) == {"x": 1.0}

    # Carefully test cached_property behavior. Cached properties which have
    # not been accessed are not in the __dict__...
    assert "tripled" not in c.__dict__
    # ...accessing them adds them to the __dict__...
    _ = c.tripled
    assert "tripled" in c.__dict__

    # ...but they still don't appear in the asdict output
    assert chz.asdict(c) == {"x": 1.0}


def test_replace():
    @chz.chz
    class X:
        a: int
        b: int

    x = X(a=1, b=2)

    y = chz.replace(x, a=3)
    assert y is not x
    assert x.a == 1
    assert x.b == 2
    assert y.a == 3
    assert y.b == 2

    z = chz.replace(y, a=4, b=5)
    assert z is not x
    assert z is not y
    assert y.a == 3
    assert y.b == 2
    assert z.a == 4
    assert z.b == 5

    @chz.chz
    class Y:
        a: int
        X_e: int

        @functools.cached_property
        def b(self):
            return self.a

        @property
        def c(self):
            return self.a

        @c.setter
        def c(self, value):
            self.a = value  # type: ignore

        @chz.init_property
        def d(self):
            return self.a

    y = Y(a=1, e=11)
    y = chz.replace(y, a=2)
    y = chz.replace(y, e=12)
    with pytest.raises(TypeError, match=r"__init__\(\) got an unexpected keyword argument 'b'"):
        chz.replace(y, b=1)
    with pytest.raises(TypeError, match=r"__init__\(\) got an unexpected keyword argument 'c'"):
        chz.replace(y, c=1)
    with pytest.raises(TypeError, match=r"__init__\(\) got an unexpected keyword argument 'd'"):
        chz.replace(y, d=1)
    with pytest.raises(TypeError, match=r"__init__\(\) got an unexpected keyword argument 'X_e'"):
        chz.replace(y, X_e=1)


def test_repr():
    @chz.chz
    class X:
        a: int
        b: int

    assert repr(X(a=1, b=2)) == "test_repr.<locals>.X(a=1, b=2)"

    @chz.chz
    class Y:
        X_seed1: int

        @chz.init_property
        def seed1(self):
            return self.X_seed1 + 10

    assert repr(Y(seed1=1)) == "test_repr.<locals>.Y(seed1=1)"

    @chz.chz
    class Z:
        a: int = chz.field(repr=False)
        b: int = chz.field(repr=lambda x: f"?{x}?")

    assert repr(Z(a=1, b=2)) == "test_repr.<locals>.Z(a=..., b=?2?)"


def test_eq():
    @chz.chz
    class X:
        a: int
        b: int

    x = X(a=1, b=2)
    y = X(a=1, b=2)
    z = X(a=1, b=3)
    assert x == y
    assert x != z
    assert x != 1


def test_hash():
    @chz.chz
    class X:
        a: int
        b: int

        @chz.init_property
        def c(self):
            return self.b + 1

    x = X(a=1, b=2)
    y = X(a=1, b=2)
    x2 = chz.replace(x, a=2)
    z = X(a=1, b=3)
    assert hash(x) == hash(y)
    assert hash(x) != hash(z)
    assert hash(x2) != hash(x)

    @chz.chz
    class Q:
        a: list[int] = chz.field(default_factory=lambda: [1, 2, 3])

    q = Q()
    with pytest.raises(TypeError, match=re.escape("Cannot hash chz field: Q.a=[1, 2, 3]")):
        hash(q)

    @chz.chz
    class R:
        a: tuple[int, ...] = chz.field(default_factory=lambda: (1, 2, 3))

    # Tuples are hashable.
    hash(R())

    value = 0

    @chz.chz
    class S:
        @chz.init_property
        def a(self):
            nonlocal value
            value += 1
            return value

    # Since init property is not adding a __chz_fields__
    # the instances of S result in the same hash value
    # despite not having the same a value
    s1 = S()
    s2 = S()
    assert hash(s1) == hash(s2)
    assert s1.a != s2.a

    @chz.chz
    class T:
        X_a: int

        @chz.init_property
        def a(self):
            return [self.X_a]

    with pytest.raises(TypeError):
        hash(T(a=1))

    @chz.chz
    class U:
        X_a: list[int]

        @chz.init_property
        def a(self):
            return tuple(self.X_a)

    hash(U(a=[1, 2, 3]))


def test_blueprint_values():
    @chz.chz
    class Y:
        c: int

        @chz.init_property
        def b(self):
            return self.c + 1

    @chz.chz
    class X:
        b: int
        c: Y = chz.field(default_factory=lambda: Y(c=1))

        @chz.init_property
        def a(self):
            return self.c.b + self.b

    x = X(b=2)

    assert x.a == 4  # (c=1) + 1 + (b=2)
    assert x.c.b == 2  # (c=1) + 1
    values = chz.beta_to_blueprint_values(x)
    assert values == {"b": 2, "c": Y, "c.c": 1}
    assert chz.Blueprint(X).apply(values).make() == x

    x = X(b=2, c=Y(c=3))
    assert x.a == 6  # (c=3) + 1 + (b=2)
    assert x.c.b == 4  # (c=3) + 1
    values = chz.beta_to_blueprint_values(x)
    assert values == {"b": 2, "c": Y, "c.c": 3}
    assert chz.Blueprint(X).apply(values).make() == x

    @chz.chz
    class Q:
        a: int
        b: tuple[int, ...] = chz.field(default_factory=lambda: (1, 2, 3))

    q = Q(a=1)
    values = chz.beta_to_blueprint_values(q)
    assert values == {"a": 1, "b": (1, 2, 3)}
    assert chz.Blueprint(Q).apply(values).make() == q

    @chz.chz
    class R:
        a: int
        b: list[int] = chz.field(default_factory=lambda: [1, 2, 3])

    r = R(a=1)

    # Ensure that castable + json mostly works
    values = chz.beta_to_blueprint_values(r)
    assert (
        chz.Blueprint(R)
        .apply(
            {key: chz.Castable(str(value)) for key, value in json.loads(json.dumps(values)).items()}
        )
        .make()
        == r
    )

    # This test ensures that we handle the following as expected:
    # - default_factory
    # - munged values
    # - castable values
    @chz.chz
    class T:
        default_factory: str = chz.field(default_factory=lambda: "?")
        default_value: str = chz.field(default="!")
        munged_value: str = chz.field(default="?", munger=lambda instance, value: value + "!!")

    t = T(munged_value="Hello")
    values = chz.beta_to_blueprint_values(t)
    assert values == {"default_factory": "?", "default_value": "!", "munged_value": "Hello"}
    assert chz.Blueprint(T).apply(values).make() == t

    # This test is dedicated to testing that `x_type`/`blueprint_cast` works fine
    @chz.chz
    class U:
        value: int = chz.field(x_type=str, blueprint_cast=int)

    u = U(value="7")

    # The type of the blueprint should be the one we are supposed to pass in the blueprint
    # Not the one after instantiation
    values = chz.beta_to_blueprint_values(u)
    assert values == {"value": "7"}
    assert chz.Blueprint(U).apply(values).make() == u

    # This test verifies that derived properties aren't serialized and X_ fields are not exposed
    @chz.chz
    class W:
        value: int

        @chz.init_property
        def value_2(self) -> int:
            return self.value * 2

    w = W(value=5)
    values = chz.beta_to_blueprint_values(w)
    assert values == {"value": 5}
    assert "value_2" not in values
    assert "value" in values
    assert w.value_2 == 10


def test_blueprint_values_polymorphic():
    @chz.chz
    class X:
        a: int

        @property
        def name(self) -> str:
            return "x"

    @chz.chz
    class Y(X):
        b: int

        @property
        def name(self) -> str:
            return "y"

    @chz.chz
    class Z(X):
        c: int

        @property
        def name(self) -> str:
            return "z"

    @chz.chz
    class Y2(Y):
        d: int

        @property
        def name(self) -> str:
            return "y2"

    @chz.chz
    class W:
        x: X = chz.field(meta_factory=chz.factories.subclass(base_cls=X, default_cls=Y))
        w: int

    w = W(x=Y(a=1, b=2), w=3)
    values = chz.beta_to_blueprint_values(w)
    assert values == {"x": Y, "x.a": 1, "x.b": 2, "w": 3}
    w_new = chz.Blueprint(W).apply(values).make()
    assert w_new == w
    assert w_new.x.name == "y"

    w = W(x=Z(a=1, c=2), w=3)
    values = chz.beta_to_blueprint_values(w)
    assert values == {"x": Z, "x.a": 1, "x.c": 2, "w": 3}
    w_new = chz.Blueprint(W).apply(values).make()
    assert w_new == w
    assert w_new.x.name == "z"

    w = W(x=Y2(a=1, b=2, d=3), w=4)
    values = chz.beta_to_blueprint_values(w)
    assert values == {"x": Y2, "x.a": 1, "x.b": 2, "x.d": 3, "w": 4}
    w_new = chz.Blueprint(W).apply(values).make()
    assert w_new == w
    assert w_new.x.name == "y2"

    @chz.chz
    class W_Union:
        x: Y | Z
        w: int

    wu = W_Union(x=Y(a=1, b=2), w=3)
    values = chz.beta_to_blueprint_values(wu)
    assert values == {"x": Y, "x.a": 1, "x.b": 2, "w": 3}
    wu_new = chz.Blueprint(W_Union).apply(values).make()
    assert wu_new == wu
    assert wu_new.x.name == "y"

    wu = W_Union(x=Z(a=1, c=2), w=3)
    values = chz.beta_to_blueprint_values(wu)
    assert values == {"x": Z, "x.a": 1, "x.c": 2, "w": 3}
    wu_new = chz.Blueprint(W_Union).apply(values).make()
    assert wu_new == wu
    assert wu_new.x.name == "z"


def test_blueprint_values_variadic():
    @chz.chz
    class A:
        a: int

    @chz.chz
    class B(A):
        b: int

    @chz.chz
    class Main:
        list_a: list[A]
        dict_a: dict[str, A]

    main = Main(list_a=[A(a=1), B(a=2, b=3)], dict_a={"a": A(a=4), "b": B(a=5, b=6)})
    values = chz.beta_to_blueprint_values(main)
    assert values == {
        "list_a.0": A,
        "list_a.0.a": 1,
        "list_a.1": B,
        "list_a.1.a": 2,
        "list_a.1.b": 3,
        "dict_a.a": A,
        "dict_a.a.a": 4,
        "dict_a.b": B,
        "dict_a.b.a": 5,
        "dict_a.b.b": 6,
    }
    assert chz.Blueprint(Main).apply(values).make() == main

    @chz.chz
    class Main:
        list_a: list[A | int]
        dict_a: dict[str, A | int]

    main = Main(list_a=[A(a=1), 2], dict_a={"a": A(a=4), "b": 5})
    values = chz.beta_to_blueprint_values(main)
    assert values == {
        "list_a.0": A,
        "list_a.0.a": 1,
        "list_a.1": 2,
        "dict_a.a": A,
        "dict_a.a.a": 4,
        "dict_a.b": 5,
    }
    assert chz.Blueprint(Main).apply(values).make() == main

    main = Main(list_a=[1, 2], dict_a={"a": 3, "b": 4})
    values = chz.beta_to_blueprint_values(main)
    assert values == {
        "list_a": [1, 2],
        "dict_a": {"a": 3, "b": 4},
    }
    assert chz.Blueprint(Main).apply(values).make() == main


def test_duplicate_fields():
    # There is no way to detect this since __annotations__ is a dictionary
    @chz.chz
    class X:
        a: int
        a: int  # noqa: PIE794

    X(a=1)


def test_no_type_annotation_on_field():
    with pytest.raises(TypeError, match="'a' has no type annotation"):

        @chz.chz
        class X:
            a = chz.field(default=0)


def test_logical_name():
    @chz.chz
    class X:
        X_seed1: int
        seed2: int

        @property
        def seed1(self):
            return self.X_seed1 + 100

    assert len(X.__chz_fields__) == 2
    assert X.__chz_fields__["seed1"].logical_name == "seed1"
    assert X.__chz_fields__["seed2"].logical_name == "seed2"

    x = X(seed1=1, seed2=2)
    assert x.seed1 == 101
    assert x.X_seed1 == 1
    assert x.seed2 == 2
    assert x.X_seed2 == 2


def test_init_property():
    value = 0

    @chz.chz
    class A:
        @chz.init_property
        def a(self):
            nonlocal value
            value += 1
            return value

    @chz.chz
    class B(A):
        @chz.init_property
        def b(self):
            nonlocal value
            value += 1
            return value

    b1 = B()
    assert b1.a == 1
    assert b1.b == 2

    value = 10

    b2 = B()
    assert b2.a == 11
    assert b2.b == 12

    assert b1.a == 1
    assert b1.b == 2

    @chz.chz
    class X:
        @chz.init_property
        def a(self):
            raise RuntimeError

    with pytest.raises(RuntimeError):
        X()

    @chz.chz
    class Y(X):
        pass

    with pytest.raises(RuntimeError):
        Y()


def test_init_property_top_level():
    # There isn't really anything special about init_property, you can just use it as a one-liner
    # if you don't care about static type checking. It's probably better to use a munger though
    # Note that in this case it is possible for init_property to get called more than once

    @chz.chz
    class A:
        a: int
        b = chz.init_property(lambda self: self.a + 1)

    a = A(a=1)
    assert a.__dict__ == {"X_a": 1, "a": 1, "b": 2}
    assert a.b == 2

    with pytest.raises(ValueError, match="Field 'b' is clobbered by chz.data_model.init_property"):

        @chz.chz
        class B:
            a: int
            b: int = chz.init_property(lambda self: self.a + 1)  # with type annotation


def test_default_init_property():
    @chz.chz
    class A:
        attr: int

    a = A(attr=1)
    assert a.__dict__ == {"X_attr": 1, "attr": 1}
    assert a.attr == 1
    assert a.__dict__ == {"X_attr": 1, "attr": 1}


def test_init_property_x_field():
    @chz.chz
    class A:
        X_attr: int

        @chz.init_property
        def attr(self):
            return self.X_attr + 1

    a = A(attr=1)
    assert a.X_attr == 1
    assert a.attr == 2
    assert a.__dict__ == {"X_attr": 1, "attr": 2}


def test_conflicting_superclass_no_fields_in_base():
    @chz.chz
    class BaseA:
        def method(self):
            return 1

        @property
        def prop(self):
            return 1

        @chz.init_property
        def init_prop(self):
            return 1

    with pytest.raises(
        ValueError,
        match="Cannot define field 'method' because it conflicts with something defined on a superclass",
    ):

        @chz.chz
        class A1(BaseA):
            method: int

    with pytest.raises(
        ValueError,
        match="Cannot define field 'X_method' because it conflicts with something defined on a superclass",
    ):

        @chz.chz
        class A1X(BaseA):
            X_method: int

    with pytest.raises(
        ValueError,
        match="Cannot define field 'prop' because it conflicts with something defined on a superclass",
    ):

        @chz.chz
        class A2(BaseA):
            prop: int

    with pytest.raises(
        ValueError,
        match="Cannot define field 'X_prop' because it conflicts with something defined on a superclass",
    ):

        @chz.chz
        class A2X(BaseA):
            X_prop: int

    with pytest.raises(
        ValueError,
        match="Cannot define field 'init_prop' because it conflicts with something defined on a superclass",
    ):

        @chz.chz
        class A3(BaseA):
            init_prop: int

        # We could consider allowing this. In which case, you want:
        # assert A3(init_prop=2).X_init_prop == 2
        # assert A3(init_prop=2).init_prop == 2

    with pytest.raises(
        ValueError,
        match="Cannot define field 'X_init_prop' because it conflicts with something defined on a superclass",
    ):

        @chz.chz
        class A3X(BaseA):
            X_init_prop: int


def test_conflicting_superclass_field_in_base():
    @chz.chz
    class BaseB:
        field: int = 0

    assert BaseB().X_field == 0
    assert BaseB().field == 0

    @chz.chz
    class B1(BaseB):
        X_field: int = 1

    assert B1().X_field == 1
    assert B1().field == 1

    @chz.chz
    class B2(BaseB):
        X_field: int = 1

        @chz.init_property
        def field(self):
            return self.X_field + 10

    assert B2().X_field == 1
    assert B2().field == 11

    @chz.chz
    class B3(BaseB):
        @chz.init_property
        def field(self):
            return self.X_field + 100

    assert B3().X_field == 0
    assert B3().field == 100

    @chz.chz
    class B4(BaseB):
        field: int = 1

    assert B4().X_field == 1
    assert B4().field == 1


def test_conflicting_superclass_x_field_in_base():
    @chz.chz
    class BaseC:
        X_field: int = 0

        @chz.init_property
        def field(self):
            return self.X_field + 10

    assert BaseC().X_field == 0
    assert BaseC().field == 10

    @chz.chz
    class C1(BaseC):
        X_field: int = 1

    assert C1().X_field == 1
    assert C1().field == 11

    @chz.chz
    class C2(BaseC):
        @chz.init_property
        def field(self):
            return self.X_field + 100

    assert C2().X_field == 0
    assert C2().field == 100

    with pytest.raises(ValueError, match="little unsure of what the semantics should be here"):

        @chz.chz
        class C3(BaseC):
            field: int = 1

        # assert C3().X_field == 1
        # Should this be 11 or 1?
        # The argument for 11 is that it's exactly the same case as C1
        # The argument for 1 is that it matches go-to-definition better
        # I'm in favour of 11, but I'll stick with a custom error for now...
        # assert C3().field == 11


def test_field_clobbering_in_same_class():
    with pytest.raises(ValueError, match="Field 'a' is clobbered by chz.data_model.init_property"):

        @chz.chz
        class X:
            a: int = 1

            @chz.init_property
            def a(self):
                return 1

    with pytest.raises(ValueError, match="Field 'a' is clobbered by function"):

        @chz.chz
        class Y:
            a: int = 1

            def a(self):
                return 1

    @chz.chz
    class OK1:
        # lambdas are special cased (since they're more likely to be default values than methods)
        a: typing.Callable[[], int] = lambda: 1

    @chz.chz
    class OK2:
        a: typing.Callable[[], None] = test_field_clobbering_in_same_class


def test_dataclass_errors():
    with pytest.raises(
        RuntimeError,
        match=r"Something has gone horribly awry; are you using a chz.Field in a dataclass\?",
    ):

        @dataclasses.dataclass
        class X:
            a: int = chz.field(default=1)


def test_cloudpickle_main():
    import cloudpickle  # noqa: F401

    main = """
import chz

from threading import Lock
unpickleable = Lock()

class Normal:
    def __repr__(self):
        return "normal"

assert __name__ == "__main__"

@chz.chz
class X:
    one: int
    norm: Normal = chz.field(default_factory=lambda: Normal())

import base64
import cloudpickle
print(base64.b64encode(cloudpickle.dumps(X(one=1))).decode())
"""
    import base64
    import pickle
    import subprocess
    import sys

    pickled = subprocess.check_output([sys.executable, "-c", main])
    try:
        unpickled = pickle.loads(base64.b64decode(pickled))
    except pickle.UnpicklingError as e:
        e.add_note("Maybe you forgot to remove a print statement?")
        raise
    assert unpickled.one == 1
    assert repr(unpickled) == "X(one=1, norm=normal)"


def test_protocol():
    with pytest.raises(TypeError, match="chz class cannot itself be a Protocol"):

        @chz.chz
        class Disallowed(typing.Protocol):
            a: int

    class Proto(typing.Protocol):
        a: int

    @chz.chz
    class Allowed(Proto):
        pass

    # Protocol fields do not become chz fields automatically
    Allowed()


def test_abc():
    import abc

    @chz.chz
    class IDontMakeAnyPromisesAboutBehaviourHere(abc.ABC):
        a: int

    class Abc(abc.ABC):
        a: int

    @chz.chz
    class Allowed(Abc):
        pass

    # ABC fields do not become chz fields automatically
    Allowed()


def test_pretty_format():
    from chz.data_model import pretty_format

    @chz.chz
    class Child:
        name: str
        age: int

    @chz.chz
    class Parent:
        name: str
        age: int
        X_nickname: str | None = None
        child: Child = chz.field(default_factory=lambda: Child(name="bob", age=1))

        @chz.init_property
        def nickname(self) -> str:
            return self.X_nickname or self.name

    obj = Parent(name="alice", age=30)
    expected = f"""{Parent.__qualname__}(
    age=30,
    name='alice',
    # Fields where pre-init value matches default:
    child={Child.__qualname__}(
        age=1,
        name='bob',
    ),
    nickname=None  # 'alice' (after init),
)"""
    assert pretty_format(obj, colored=False) == expected

    @chz.chz
    class Collection:
        children: list[Child]
        named_children: dict[str, Child]

    obj = Collection(
        children=[Child(name="alice", age=1)],
        named_children={"bob": Child(name="bob", age=2)},
    )
    assert (
        pretty_format(obj, colored=False)
        == """test_pretty_format.<locals>.Collection(
    children=[
        test_pretty_format.<locals>.Child(
            age=1,
            name='alice',
        ),
    ],
    named_children={
        'bob': test_pretty_format.<locals>.Child(
            age=2,
            name='bob',
        ),
    },
)"""
    )


def test_metadata():
    @chz.chz
    class X:
        a: int = chz.field(metadata={"foo": "bar"})

    assert X.__chz_fields__["a"].metadata == {"foo": "bar"}
