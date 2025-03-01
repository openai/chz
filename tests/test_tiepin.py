# ruff: noqa: UP006
# ruff: noqa: UP007
# ruff: noqa: UP045
import collections.abc
import enum
import fractions
import pathlib
import re
import sys
import typing

import pytest
import typing_extensions

from chz.tiepin import (
    CastError,
    _simplistic_try_cast,
    _simplistic_type_of_value,
    approx_type_hash,
    is_subtype,
    is_subtype_instance,
    type_repr,
)


def test_type_repr():
    assert type_repr(int) == "int"
    assert type_repr(list[int]) == "list[int]"

    class X: ...

    assert type_repr(X) == "test_tiepin:test_type_repr.<locals>.X"

    assert type_repr(typing.Literal["asdf"]) == "Literal['asdf']"
    assert type_repr(typing.Union[int, str]) == "Union[int, str]"
    assert (
        type_repr(typing.Callable[[int], X])
        == "Callable[[int], test_tiepin.test_type_repr.<locals>.X]"
    )

    assert type_repr(typing.Sequence[str]) == "Sequence[str]"
    assert type_repr(collections.abc.Sequence[str]) == "Sequence[str]"


def test_is_subtype_instance_basic():
    assert is_subtype_instance(None, None)
    assert is_subtype_instance(1, int)
    assert is_subtype_instance(True, bool)

    assert not is_subtype_instance("str", int)
    assert not is_subtype_instance(1, str)

    assert not is_subtype_instance(int, int)
    assert not is_subtype_instance(int, float)

    class A: ...

    class B(A): ...

    assert is_subtype_instance(A(), A)
    assert is_subtype_instance(B(), B)
    assert is_subtype_instance(B(), A)
    assert not is_subtype_instance(A(), B)

    assert not is_subtype_instance(A, A)
    assert not is_subtype_instance(B, A)
    assert not is_subtype_instance(A, B)
    assert not is_subtype_instance(B, B)


def test_is_subtype_instance_user_defined_generic():
    T = typing.TypeVar("T")

    class X(typing.Generic[T]): ...

    assert is_subtype_instance(X(), X)
    assert is_subtype_instance(X(), X[int])
    assert is_subtype_instance(X(), X[str])

    # Note that we do use __orig_class__ where possible
    assert is_subtype_instance(X[int](), X[int])
    assert not is_subtype_instance(X[str](), X[int])


def test_is_subtype_instance_user_defined_generic_abc():
    T = typing.TypeVar("T")

    class X(typing.Generic[T]):
        def unrelated(self) -> T: ...

        def __iter__(self):
            return iter([1, 2, 3])

    assert is_subtype_instance(X(), X)
    assert is_subtype_instance(X(), X[int])
    assert is_subtype_instance(X(), X[str])

    assert is_subtype_instance(X(), collections.abc.Iterable)
    assert is_subtype_instance(X(), collections.abc.Iterable[int])
    assert not is_subtype_instance(X(), collections.abc.Iterable[str])

    class Y(typing.Generic[T]):
        def __call__(self, x: int) -> str: ...

    assert is_subtype_instance(Y(), Y)
    assert is_subtype_instance(Y(), Y[int])
    assert is_subtype_instance(Y(), Y[str])
    assert is_subtype_instance(Y(), Y[bytes])

    assert is_subtype_instance(Y(), typing.Callable)
    assert is_subtype_instance(Y(), typing.Callable[[int], str])
    assert not is_subtype_instance(Y(), typing.Callable[[int], int])
    assert not is_subtype_instance(Y(), typing.Callable[[str], int])
    assert not is_subtype_instance(Y(), typing.Callable[[str], str])


def test_is_subtype_instance_duck_type():
    assert is_subtype_instance(1, int)
    assert is_subtype_instance(1, float)
    assert is_subtype_instance(1, complex)

    assert not is_subtype_instance(1.0, int)
    assert is_subtype_instance(1.0, float)
    assert is_subtype_instance(1.0, complex)

    assert not is_subtype_instance(1 + 1j, int)
    assert not is_subtype_instance(1 + 1j, float)
    assert is_subtype_instance(1 + 1j, complex)

    assert is_subtype_instance(bytearray(), bytes)
    assert is_subtype_instance(memoryview(b""), bytes)
    assert not is_subtype_instance(bytes(), bytearray)


def test_is_subtype_instance_any():
    assert is_subtype_instance(1, typing.Any)
    assert is_subtype_instance("str", typing.Any)
    assert is_subtype_instance([], typing.Any)
    assert is_subtype_instance(int, typing.Any)

    if sys.version_info >= (3, 11):

        class Mock(typing.Any): ...

        assert is_subtype_instance(Mock(), typing.Any)
        assert is_subtype_instance(Mock(), int)
        assert is_subtype_instance(Mock(), str)
        assert not is_subtype_instance(1, Mock)


def test_is_subtype_instance_list_abc():
    T = typing.TypeVar("T")

    seq: typing.Any
    for seq in (
        list,
        typing.List,
        collections.abc.Sequence,
        collections.abc.Iterable,
        typing.Iterable,
        collections.abc.Collection,
        list[T],
        typing.List[T],
        collections.abc.Sequence[T],
        collections.abc.Iterable[T],
        typing.Iterable[T],
        collections.abc.Collection[T],
    ):
        assert is_subtype_instance([], seq)
        assert is_subtype_instance([], seq[int])
        assert is_subtype_instance([], seq[object])
        assert is_subtype_instance([], seq[typing.Any])

        assert is_subtype_instance([1, 2], seq)
        assert is_subtype_instance([1, 2], seq[int])
        assert is_subtype_instance([1, 2], seq[object])
        assert is_subtype_instance([1, 2], seq[typing.Any])
        assert not is_subtype_instance([1, 2], seq[str])

        assert is_subtype_instance([1, 2, "3"], seq)
        assert is_subtype_instance([1, 2, "3"], seq[object])
        assert is_subtype_instance([1, 2, "3"], seq[typing.Any])
        assert not is_subtype_instance([1, 2, "3"], seq[int])


def test_is_subtype_instance_iterable():
    assert is_subtype_instance([], typing.Iterable)
    assert is_subtype_instance([1, 2, 3], typing.Iterable[int])
    assert not is_subtype_instance([1, 2, "3"], typing.Iterable[int])

    assert is_subtype_instance((), typing.Iterable)
    assert is_subtype_instance((1, 2, 3), typing.Iterable[int])
    assert not is_subtype_instance((1, 2, "3"), typing.Iterable[int])

    assert is_subtype_instance({}, typing.Iterable)
    assert is_subtype_instance({1: 2, 3: 4}, typing.Iterable[int])
    assert not is_subtype_instance({1: 2, "3": 4}, typing.Iterable[int])

    assert is_subtype_instance(set(), typing.Iterable)
    assert is_subtype_instance({1, 2, 3}, typing.Iterable[int])
    assert not is_subtype_instance({1, 2, "3"}, typing.Iterable[int])

    assert is_subtype_instance(frozenset(), typing.Iterable)
    assert is_subtype_instance(frozenset({1, 2, 3}), typing.Iterable[int])
    assert not is_subtype_instance(frozenset({1, 2, "3"}), typing.Iterable[int])

    assert is_subtype_instance("", typing.Iterable)
    assert is_subtype_instance("123", typing.Iterable[str])
    assert not is_subtype_instance("123", typing.Iterable[int])

    assert is_subtype_instance(b"", typing.Iterable)
    assert is_subtype_instance(b"123", typing.Iterable[int])
    assert not is_subtype_instance(b"123", typing.Iterable[str])

    assert is_subtype_instance(bytearray(), typing.Iterable)
    assert is_subtype_instance(bytearray(b"123"), typing.Iterable[int])
    assert not is_subtype_instance(bytearray(b"123"), typing.Iterable[str])

    assert is_subtype_instance(memoryview(b""), typing.Iterable)
    assert is_subtype_instance(memoryview(b"123"), typing.Iterable[int])
    assert not is_subtype_instance(memoryview(b"123"), typing.Iterable[str])

    assert is_subtype_instance(range(0), typing.Iterable)
    assert is_subtype_instance(range(3), typing.Iterable[int])
    assert not is_subtype_instance(range(3), typing.Iterable[str])

    assert is_subtype_instance(map(int, [1, 2, 3]), typing.Iterable)
    assert is_subtype_instance(map(int, [1, 2, 3]), typing.Iterable[int])
    assert not is_subtype_instance(map(str, [1, 2, 3]), typing.Iterable[int])


def test_is_subtype_instance_tuple():
    assert is_subtype_instance((1, 2), tuple)
    assert is_subtype_instance((1, 2), tuple[int, int])
    assert is_subtype_instance((1, 2), tuple[int, ...])
    assert is_subtype_instance((1, 2), typing.Tuple)
    assert is_subtype_instance((1, 2), typing.Tuple[int, int])
    assert is_subtype_instance((1, 2), typing.Tuple[int, ...])

    assert not is_subtype_instance((1, 2), tuple[int, int, int])
    assert not is_subtype_instance((1, 2), tuple[int, str])
    assert not is_subtype_instance((1, 2), typing.Tuple[int, int, int])
    assert not is_subtype_instance((1, 2), typing.Tuple[int, str])

    assert is_subtype_instance((1, "str", "bytes"), tuple)
    assert is_subtype_instance((1, "str", "bytes"), tuple[int, str, str])
    assert is_subtype_instance((1, "str", "bytes"), typing.Tuple)
    assert is_subtype_instance((1, "str", "bytes"), typing.Tuple[int, str, str])

    assert not is_subtype_instance((1, "str", "bytes"), tuple[int, ...])


def test_is_subtype_instance_mapping():
    K = typing.TypeVar("K")
    V = typing.TypeVar("V")

    map: typing.Any
    for map in (
        dict,
        typing.Dict,
        collections.abc.MutableMapping,
        collections.abc.Mapping,
        dict[K, V],
        typing.Dict[K, V],
        collections.abc.MutableMapping[K, V],
        collections.abc.Mapping[K, V],
    ):
        assert is_subtype_instance({}, map)
        assert is_subtype_instance({}, map[str, int])

        assert is_subtype_instance({"a": 1}, map)
        assert is_subtype_instance({"a": 1}, map[str, int])
        assert is_subtype_instance({"a": 1}, map[str, typing.Any])
        assert is_subtype_instance({"a": 1}, map[typing.Any, typing.Any])

        assert not is_subtype_instance({"a": 1}, map[int, int])
        assert not is_subtype_instance({"a": 1}, map[int, typing.Any])


def test_is_subtype_instance_typed_dict():
    for t_TypedDict in (typing.TypedDict, typing_extensions.TypedDict):

        class A(t_TypedDict):
            a: int
            b: str

        class B(A):
            c: bytes

        assert not is_subtype_instance({}, A)
        assert not is_subtype_instance({"a": 1}, A)

        assert is_subtype_instance({"a": 1, "b": "str"}, A)
        assert not is_subtype_instance({"a": 1, "b": "str"}, B)

        assert is_subtype_instance({"a": 1, "b": "str", "c": b"bytes"}, A)
        assert is_subtype_instance({"a": 1, "b": "str", "c": b"bytes"}, B)

        assert not is_subtype_instance({"a": 1, "b": 1}, A)

        assert not is_subtype_instance({"c": b"bytes"}, A)
        assert not is_subtype_instance({"c": b"bytes"}, B)


def test_is_subtype_instance_typed_dict_required():
    for t_TypedDict in (typing.TypedDict, typing_extensions.TypedDict):

        class Foo(t_TypedDict):
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

        class Qux(t_TypedDict, total=False):
            j: int

        assert not is_subtype_instance({}, Foo)
        assert is_subtype_instance({"a": 1, "b": 1}, Foo)
        assert not is_subtype_instance({"a": 1, "b": "str"}, Foo)
        assert is_subtype_instance({"a": 1, "b": 1, "c": 1}, Foo)
        assert not is_subtype_instance({"a": 1, "b": 1, "c": "str"}, Foo)
        assert is_subtype_instance({"a": 1, "b": 1, "c": 1, "xyz": object()}, Foo)

        assert not is_subtype_instance({}, Bar)
        assert not is_subtype_instance({"a": 1, "b": 1}, Bar)
        assert is_subtype_instance({"a": 1, "b": 1, "e": 1}, Bar)
        assert is_subtype_instance({"a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1}, Bar)
        assert not is_subtype_instance({"a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": "str"}, Bar)

        assert not is_subtype_instance({"a": 1, "b": 1, "e": 1}, Baz)
        assert is_subtype_instance({"a": 1, "b": 1, "e": 1, "g": 1, "h": 1}, Baz)

        assert is_subtype_instance({}, Qux)
        assert is_subtype_instance({"j": 1}, Qux)
        assert not is_subtype_instance({"j": "str"}, Qux)


def test_is_subtype_instance_named_tuple():
    class A(typing.NamedTuple):
        a: int
        b: str

    class B(A): ...

    assert is_subtype_instance(A(a=1, b="str"), A)
    assert is_subtype_instance(A(a=1, b="str"), tuple[int, str])
    assert not is_subtype_instance(A(a=1, b="str"), tuple[int, int])
    assert not is_subtype_instance(A(a=1, b="str"), B)


def test_is_subtype_instance_type_var():
    T = typing.TypeVar("T")
    assert is_subtype_instance(1, T)
    assert is_subtype_instance("str", T)

    assert is_subtype_instance([1, 2], list[T])
    assert is_subtype_instance((1,), tuple[T])

    assert is_subtype_instance("a", typing.AnyStr)
    assert not is_subtype_instance(1, typing.AnyStr)

    assert is_subtype_instance(["a"], list[typing.AnyStr])
    assert is_subtype_instance(["a"], typing.List[typing.AnyStr])
    assert not is_subtype_instance([1], list[typing.AnyStr])

    assert is_subtype_instance(["this is", b"not quite right"], list[typing.AnyStr])

    C = typing.TypeVar("C", list[int], list[str])
    assert is_subtype_instance([], C)
    assert not is_subtype_instance([b"bytes"], C)

    B = typing.TypeVar("B", bound=int)

    assert is_subtype_instance(1, B)
    assert is_subtype_instance(False, B)
    assert not is_subtype_instance("str", B)


def test_is_subtype_instance_union():
    assert is_subtype_instance(1, typing.Union[int, str])
    assert is_subtype_instance("str", typing.Union[int, str])
    assert not is_subtype_instance(b"bytes", typing.Union[int, str])

    assert is_subtype_instance([1], typing.List[typing.Union[int, str]])
    assert is_subtype_instance(["str", 1], typing.List[typing.Union[int, str]])
    assert is_subtype_instance([1], list[typing.Union[int, str]])
    assert is_subtype_instance(["str", 1], list[typing.Union[int, str]])

    if sys.version_info >= (3, 10):
        assert is_subtype_instance(1, int | str)
        assert is_subtype_instance("str", int | str)
        assert not is_subtype_instance(b"bytes", int | str)

        assert is_subtype_instance([1], typing.List[int | str])
        assert is_subtype_instance(["str", 1], typing.List[int | str])
        assert is_subtype_instance([1], list[int | str])
        assert is_subtype_instance(["str", 1], list[int | str])


def test_is_subtype_instance_callable() -> None:
    # lambda / untyped subtyping
    assert is_subtype_instance(lambda: None, typing.Callable)
    assert is_subtype_instance(lambda x: x, typing.Callable)

    assert is_subtype_instance(lambda: None, typing.Callable[[], None])
    assert is_subtype_instance(lambda x: x, typing.Callable[[int], int])

    assert is_subtype_instance(lambda: None, typing.Callable[..., None])
    assert is_subtype_instance(lambda x: x, typing.Callable[..., int])

    assert not is_subtype_instance(lambda: None, typing.Callable[[int], int])
    assert not is_subtype_instance(lambda x: x, typing.Callable[[], None])

    assert not is_subtype_instance(1, typing.Callable[[int], str])

    # typed functions subtyping
    def foo(x: int, y: str, z: bytes = ...) -> None: ...

    assert is_subtype_instance(foo, typing.Callable[[int, str], None])
    assert is_subtype_instance(foo, typing.Callable[[int, str, bytes], None])
    assert not is_subtype_instance(foo, typing.Callable[[str, int, bytes], None])
    assert not is_subtype_instance(foo, typing.Callable[[int, str, bytes], str])

    def bar(x: object) -> bool: ...

    assert is_subtype_instance(bar, typing.Callable[[int], int])
    assert is_subtype_instance(bar, typing.Callable[[str], bool])
    assert is_subtype_instance(bar, typing.Callable[..., bool])
    assert not is_subtype_instance(bar, typing.Callable[..., str])

    def baz(x, y, z): ...

    assert is_subtype_instance(baz, typing.Callable[[int, str, bytes], int])
    assert is_subtype_instance(baz, typing.Callable[[str, bytes, int], bytes])

    # type subtyping
    class A:
        def __init__(self, x: int) -> None: ...

    class B(A): ...

    assert is_subtype_instance(A, typing.Callable[[int], A])
    assert is_subtype_instance(B, typing.Callable[[int], A])
    assert not is_subtype_instance(A, typing.Callable[[int], B])

    # callable instance subtyping
    class Call:
        def __call__(self, x: int) -> None: ...

    assert is_subtype_instance(Call(), typing.Callable[[int], None])
    assert is_subtype_instance(Call(), typing.Callable[..., None])
    assert not is_subtype_instance(Call(), typing.Callable[[str], None])
    assert not is_subtype_instance(Call(), typing.Callable[[int, int], None])

    # function with arguments of generic type
    def takes_dict(x: dict[int, str]) -> int: ...

    assert is_subtype_instance(takes_dict, typing.Callable[[dict[int, str]], int])
    assert is_subtype_instance(takes_dict, typing.Callable[[dict[int, typing.Any]], int])
    assert is_subtype_instance(takes_dict, typing.Callable[[dict[typing.Any, str]], int])
    assert is_subtype_instance(takes_dict, typing.Callable[[dict[typing.Any, typing.Any]], int])
    assert not is_subtype_instance(takes_dict, typing.Callable[[dict[object, object]], int])
    assert not is_subtype_instance(takes_dict, typing.Callable[[dict[int, str]], None])
    assert not is_subtype_instance(takes_dict, typing.Callable[[dict[str, int]], int])

    # more contravariance tests
    class C(B): ...

    def takes_b(x: B) -> None: ...

    assert is_subtype_instance(takes_b, typing.Callable[[C], None])
    assert is_subtype_instance(takes_b, typing.Callable[[B], None])
    assert not is_subtype_instance(takes_b, typing.Callable[[A], None])

    # varargs
    def varargs(*args: int) -> None: ...

    assert is_subtype_instance(varargs, typing.Callable[[int], None])
    assert is_subtype_instance(varargs, typing.Callable[[int, int], None])
    assert not is_subtype_instance(varargs, typing.Callable[[str], None])

    # varkwargs
    def varkwargs(**kwargs: int) -> None: ...

    assert is_subtype_instance(varkwargs, typing.Callable[[], None])
    assert not is_subtype_instance(varkwargs, typing.Callable[[int], None])
    assert not is_subtype_instance(varkwargs, typing.Callable[[int, int], None])

    # param spec
    P = typing.ParamSpec("P")
    assert not is_subtype_instance(lambda: None, typing.Callable[[P], None])
    assert not is_subtype_instance(lambda: foo, typing.Callable[[P], None])
    assert not is_subtype_instance(lambda: bar, typing.Callable[[P], None])
    assert not is_subtype_instance(lambda: A, typing.Callable[[P], None])


def test_is_subtype_instance_callable_protocol():
    class A: ...

    class B(A): ...

    class C(B): ...

    class P1(typing.Protocol):
        def __call__(self, x: B) -> None: ...

    def p1(x: B) -> None: ...
    def p2(x: A) -> None: ...
    def p3(x: B = ...) -> None: ...
    def p4(x: B, y: int = ...) -> None: ...

    assert is_subtype_instance(p1, P1)
    assert is_subtype_instance(p2, P1)
    assert is_subtype_instance(p3, P1)
    assert is_subtype_instance(p4, P1)

    def p5(x: B, /) -> None: ...
    def p6(y: B, /) -> None: ...
    def p7(x: C) -> None: ...
    def p8(y: B) -> None: ...
    def p9(x: B, y: int) -> None: ...

    assert not is_subtype_instance(p5, P1)
    assert not is_subtype_instance(p6, P1)
    assert not is_subtype_instance(p7, P1)
    assert not is_subtype_instance(p8, P1)
    assert not is_subtype_instance(p9, P1)

    class P2(typing.Protocol):
        def __call__(self, x: B, /) -> None: ...

    assert is_subtype_instance(p1, P2)
    assert is_subtype_instance(p2, P2)
    assert is_subtype_instance(p3, P2)
    assert is_subtype_instance(p4, P2)
    assert is_subtype_instance(p5, P2)
    assert is_subtype_instance(p6, P2)

    class P3(typing.Protocol):
        def __call__(self, x: B, y: int = ...) -> None: ...

    assert not is_subtype_instance(p1, P3)
    assert not is_subtype_instance(p9, P3)

    def p10(*args: int | A) -> None: ...
    def p11(*args: int | C) -> None: ...

    assert is_subtype_instance(p10, P3)
    assert not is_subtype_instance(p11, P3)

    class P4(typing.Protocol):
        def __call__(self, x: B, *, y: int) -> None: ...

    assert not is_subtype_instance(p1, P4)
    assert is_subtype_instance(p4, P4)

    def p12(x: B, *, y: int = ...) -> None: ...
    def p13(x: B, *, y: int) -> None: ...
    def p14(x: B, *, y: B = ...) -> None: ...
    def p15(**kwargs: int | B) -> None: ...
    def p16(x: B, **kwargs: int) -> None: ...
    def p17(x: B, *, y: int, z: int = ...) -> None: ...
    def p18(x: B, y: B) -> None: ...

    assert is_subtype_instance(p4, P4)
    assert is_subtype_instance(p9, P4)
    assert is_subtype_instance(p12, P4)
    assert is_subtype_instance(p13, P4)
    assert not is_subtype_instance(p14, P4)
    assert not is_subtype_instance(p15, P4)
    assert not is_subtype_instance(p16, P4)
    assert is_subtype_instance(p17, P4)
    assert not is_subtype_instance(p18, P4)

    class P5(typing.Protocol):
        def __call__(self, x: B, *, y: int = ...) -> None: ...

    assert is_subtype_instance(p4, P5)
    assert not is_subtype_instance(p9, P5)
    assert is_subtype_instance(p12, P5)
    assert not is_subtype_instance(p13, P5)
    assert not is_subtype_instance(p14, P5)
    assert not is_subtype_instance(p15, P5)
    assert not is_subtype_instance(p16, P5)
    assert not is_subtype_instance(p17, P5)
    assert not is_subtype_instance(p18, P5)

    class P7(typing.Protocol):
        def __call__(self, x: B, **kwargs: B) -> None: ...

    assert not is_subtype_instance(p1, P7)
    assert not is_subtype_instance(p4, P7)
    assert not is_subtype_instance(p12, P7)

    def p19(x: B, **kwargs: A) -> None: ...
    def p20(x: B, **kwargs: C) -> None: ...
    def p21(x: B, y: B, **kwargs: B) -> None: ...
    def p22(x: B, *, y: B, **kwargs: B) -> None: ...
    def p23(x: B, *, y: int, **kwargs: B) -> None: ...

    assert is_subtype_instance(p19, P7)
    assert not is_subtype_instance(p20, P7)
    assert not is_subtype_instance(p21, P7)
    assert is_subtype_instance(p22, P7)
    assert not is_subtype_instance(p23, P7)

    class P8(typing.Protocol):
        def __call__(self) -> B: ...

    def p22() -> A: ...
    def p23() -> C: ...

    assert not is_subtype_instance(p22, P8)
    assert is_subtype_instance(p23, P8)


def test_is_subtype_instance_protocol_chz_callable():
    class P(typing.Protocol):
        def __call__(self, a: int) -> int: ...

    import chz

    @chz.chz
    class Bad:
        def __call__(self) -> int: ...

    @chz.chz
    class Good:
        def __call__(self, a: int) -> int: ...

    assert not is_subtype_instance(Bad(), P)
    assert not is_subtype_instance(Bad, P)
    assert is_subtype_instance(Good(), P)
    assert not is_subtype_instance(Good, P)


def test_is_subtype_instance_protocol_attr():
    class A: ...

    class B(A): ...

    class C(B): ...

    class FooProto(typing.Protocol):
        x: B

        def foo(self) -> int: ...

    class Foo:
        def __init__(self, x) -> None:
            self.x = x

        def foo(self) -> int:
            return 1

    assert not is_subtype_instance(Foo(A()), FooProto)
    assert is_subtype_instance(Foo(B()), FooProto)
    assert is_subtype_instance(Foo(C()), FooProto)

    b = Foo(B())
    b.foo = 1
    assert not is_subtype_instance(b, FooProto)

    assert not is_subtype_instance(object(), FooProto)


def test_is_subtype_instance_runtime_protocol():
    @typing.runtime_checkable
    class FooProto(typing.Protocol):
        def foo(self) -> int: ...

    class Foo:
        def foo(self) -> int:
            return 1

    assert is_subtype_instance(Foo(), FooProto)
    assert not is_subtype_instance(object(), FooProto)


def test_is_subtype_instance_literal():
    assert is_subtype_instance(1, typing.Literal[1])
    assert is_subtype_instance("str", typing.Literal["str"])

    assert is_subtype_instance(1, typing.Literal[1, 2])
    assert is_subtype_instance("str", typing.Literal[1, "str"])

    assert not is_subtype_instance(1, typing.Literal[2])
    assert not is_subtype_instance("str", typing.Literal[1, "bytes"])

    assert is_subtype_instance(None, typing.Literal[None])
    assert is_subtype_instance(None, typing.Literal[1, "bytes", None])


def test_is_subtype_instance_type():
    assert is_subtype_instance(int, type)
    assert is_subtype_instance(str, type)
    assert is_subtype_instance(type, type)
    assert is_subtype_instance(int, typing.Type)
    assert is_subtype_instance(str, typing.Type)
    assert is_subtype_instance(type, typing.Type)

    assert is_subtype_instance(int, type[int])
    assert is_subtype_instance(str, type[str])
    assert is_subtype_instance(type, type[type])
    assert is_subtype_instance(int, typing.Type[int])
    assert is_subtype_instance(str, typing.Type[str])
    assert is_subtype_instance(type, typing.Type[type])

    assert not is_subtype_instance(int, type[str])
    assert not is_subtype_instance(str, type[int])
    assert not is_subtype_instance(type, type[int])
    assert not is_subtype_instance(int, typing.Type[str])
    assert not is_subtype_instance(str, typing.Type[int])
    assert not is_subtype_instance(type, typing.Type[int])


def test_is_subtype_instance_enum():
    class Color(enum.Enum):
        RED = 1
        GREEN = 2

    assert is_subtype_instance(Color.RED, enum.Enum)
    assert is_subtype_instance(Color.RED, Color)

    assert not is_subtype_instance(1, Color)
    assert not is_subtype_instance("RED", Color)

    assert is_subtype_instance(Color.RED, typing.Literal[Color.RED])
    assert is_subtype_instance(Color.RED, typing.Literal[Color.RED, Color.GREEN])
    assert not is_subtype_instance(Color.RED, typing.Literal[Color.GREEN])


def test_is_subtype_instance_new_type():
    N = typing.NewType("N", int)

    assert is_subtype_instance(1, N)
    assert not is_subtype_instance("1", N)


def test_is_subtype_instance_literal_string():
    assert is_subtype_instance("str", typing.LiteralString)
    assert not is_subtype_instance(1, typing.LiteralString)


def test_is_subtype_instance_explicit_protocol_lsp_violation():
    class P(typing.Protocol):
        def makes_int(self) -> int: ...

    class Implicit:
        def makes_int(self) -> str: ...

    class Explicit(P):
        def makes_int(self) -> str: ...

    assert not is_subtype_instance(Implicit(), P)
    assert is_subtype_instance(Explicit(), P)


def test_is_subtype_instance_pydantic() -> None:
    import pydantic

    T = typing.TypeVar("T")

    class Thing(pydantic.BaseModel, typing.Generic[T]):
        type: str = "thing"
        x: T

    assert is_subtype_instance(Thing[int](x=5), Thing)


def test_is_subtype_instance_pydantic_utils() -> None:
    import pydantic
    import pydantic_core

    try:
        from pydantic_utils import get_polymorphic_generic_model_schema
    except ImportError:
        pytest.skip("pydantic_utils not installed")

    T = typing.TypeVar("T")

    class Foo(pydantic.BaseModel, typing.Generic[T]):
        type: str = "foo"
        x: T

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            source: typing.Type[pydantic.BaseModel],  # noqa: UP006
            handler: pydantic.GetCoreSchemaHandler,
        ) -> pydantic_core.core_schema.CoreSchema:
            return get_polymorphic_generic_model_schema(
                cls,
                __class__,
                source,
                handler,  # type:ignore[name-defined]
            )

    class Bar(Foo[T], typing.Generic[T]):
        type: str = "bar"
        y: T

    assert is_subtype_instance(Foo[int](x=5), Foo)
    assert Foo[typing.Any].model_validate(Foo[int](x=5))
    assert is_subtype_instance(Foo[int](x=5), Foo[typing.Any])
    assert is_subtype_instance(Bar[int](x=5, y=2), Foo[int])
    # This is currently broken in pydantic_utils.
    # assert not is_subtype_instance(Bar[str](x="a", y="b"), Foo[int])
    assert is_subtype_instance(Bar(x=5, y=2), Foo[int])


def test_is_subtype():
    assert is_subtype(int, int)
    assert not is_subtype(int, str)

    assert is_subtype(list, list)
    assert is_subtype(list[int], list)
    assert is_subtype(list, list[int])
    assert is_subtype(list[int], list[typing.Any])
    assert is_subtype(list[typing.Any], list[int])
    assert not is_subtype(list[int], list[str])

    class A: ...

    class B(A): ...

    assert is_subtype(tuple, tuple)
    assert is_subtype(tuple[int], tuple[int, ...])
    assert is_subtype(tuple[int, int], tuple[int, ...])
    assert not is_subtype(tuple[int, ...], tuple[int, int])
    assert not is_subtype(tuple[int, str], tuple[int, ...])

    assert is_subtype(tuple[B, B], tuple[A, B])
    assert not is_subtype(tuple[B, A], tuple[B, B])
    assert not is_subtype(tuple[B, B], tuple[A, B, object])

    assert is_subtype(dict, dict)
    assert is_subtype(dict[typing.Any, B], dict[str, A])
    assert not is_subtype(dict[A, A], dict[A, B])

    assert is_subtype(int, int | str)
    assert is_subtype(str, int | str)
    assert not is_subtype(bytes, int | str)

    assert is_subtype(int | str, str | int)
    assert is_subtype(int | str, int | bytes | str)
    assert not is_subtype(int | str | bytes, int | str)

    assert is_subtype(int, typing.Union[int, str])
    assert is_subtype(str, typing.Union[int, str])
    assert not is_subtype(bytes, typing.Union[int, str])

    assert is_subtype(typing.Union[int, str], typing.Union[str, int])
    assert is_subtype(typing.Union[int, str], typing.Union[int, bytes, str])
    assert not is_subtype(typing.Union[int, str, bytes], typing.Union[int, str])

    assert is_subtype(None, None)
    assert is_subtype(None, int | None)
    assert is_subtype(None, typing.Optional[int])

    assert is_subtype(typing.Literal[1, 2], typing.Literal[3, 2, 1])
    assert not is_subtype(typing.Literal[1, 2, 4], typing.Literal[3, 2, 1])
    assert is_subtype(typing.Literal[1, 2], str | int)
    assert is_subtype(typing.Literal[1, 2], str | typing.Literal[1, 2, 3])

    assert is_subtype(typing.Callable[[int], str], typing.Callable[[int], str])
    assert not is_subtype(typing.Callable[[int], str], typing.Callable[[int, int], str])
    assert is_subtype(typing.Callable[[int], str], typing.Callable[[int], str | None])
    assert not is_subtype(typing.Callable[[int], str | None], typing.Callable[[int], str])
    assert is_subtype(typing.Callable[[int | None], None], typing.Callable[[int], None])
    assert not is_subtype(typing.Callable[[int], None], typing.Callable[[int | None], None])
    assert not is_subtype(typing.Callable[[int], None], typing.Callable[[str], None])


def test_is_subtype_protocol():
    class P1(typing.Protocol):
        def foo(self) -> int: ...

    class P2(typing.Protocol):
        def foo(self) -> int: ...
        def bar(self) -> int: ...

    class Good:
        def foo(self) -> int: ...

    class Bad:
        def bar(self) -> int: ...

    assert not is_subtype(P1, P2)
    assert is_subtype(P2, P1)

    assert is_subtype(Good, P1)
    assert not is_subtype(Bad, P1)
    assert not is_subtype(Good, P2)

    def a() -> P1: ...

    assert is_subtype_instance(a, typing.Callable[..., P1])
    assert not is_subtype_instance(a, typing.Callable[..., P2])


def test_no_return():
    assert is_subtype_instance(typing.NoReturn, int)
    assert is_subtype_instance(typing.NoReturn, str)

    def foo() -> typing.NoReturn: ...

    assert is_subtype_instance(foo, typing.Callable[[], None])
    assert is_subtype_instance(foo, typing.Callable[[], str])

    if sys.version_info >= (3, 11):
        assert is_subtype_instance(typing.Never, int)
        assert is_subtype_instance(typing.Never, str)

        def foo() -> typing.Never: ...

        assert is_subtype_instance(foo, typing.Callable[[], None])
        assert is_subtype_instance(foo, typing.Callable[[], str])


def test_try_cast_object_any():
    for obj_any in (object, typing.Any, typing_extensions.Any):
        assert _simplistic_try_cast("1", obj_any) == 1
        assert _simplistic_try_cast("1a", obj_any) == "1a"
        assert _simplistic_try_cast("1j", obj_any) == 1j
        assert _simplistic_try_cast("{1: ('2', [3])}", obj_any) == {1: ("2", [3])}
        assert _simplistic_try_cast("null", obj_any) is None
        assert _simplistic_try_cast("none", obj_any) is None
        assert _simplistic_try_cast("true", obj_any) is True
        assert _simplistic_try_cast("false", obj_any) is False


def test_try_cast_tuple():
    assert _simplistic_try_cast("1", tuple) == ("1",)
    assert _simplistic_try_cast("1,2", tuple) == ("1", "2")
    assert _simplistic_try_cast("1,2", tuple[str, str]) == ("1", "2")
    assert _simplistic_try_cast("1,2", tuple[typing.Any, ...]) == (1, 2)
    assert _simplistic_try_cast("1a,2", tuple[typing.Any, ...]) == ("1a", 2)
    assert _simplistic_try_cast("1,2", tuple[int, ...]) == (1, 2)
    assert _simplistic_try_cast("", tuple) == ()

    # can't distinguish untyped tuple from zero length tuple
    assert _simplistic_try_cast("1", tuple[()]) == ("1",)
    assert _simplistic_try_cast("1,2", tuple[()]) == ("1", "2")


def test_try_cast_list():
    assert _simplistic_try_cast("1", list) == [1]
    assert _simplistic_try_cast("1,str", list) == [1, "str"]
    assert _simplistic_try_cast("1,2", list[int]) == [1, 2]
    assert _simplistic_try_cast("1,2", list[str]) == ["1", "2"]

    assert _simplistic_try_cast("[1]", list) == [1]
    assert _simplistic_try_cast("[1,'str']", list) == [1, "str"]
    assert _simplistic_try_cast("[1,2]", list[int]) == [1, 2]

    with pytest.raises(CastError, match=r"Could not cast '\[1,2\]' to list\[str\]"):
        _simplistic_try_cast("[1,2]", list[str])
    with pytest.raises(CastError, match=r"Could not cast '\[1,str\]' to list"):
        _simplistic_try_cast("[1,str]", list)


def test_try_cast_sequence_iterable():
    for origin in {
        collections.abc.Sequence,
        collections.abc.Iterable,
        typing.Sequence,
        typing.Iterable,
    }:
        assert _simplistic_try_cast("1", origin) == (1,)
        assert _simplistic_try_cast("1,str", origin) == (1, "str")
        assert _simplistic_try_cast("1,2", origin[int]) == (1, 2)
        assert _simplistic_try_cast("1,2", origin[str]) == ("1", "2")

        assert _simplistic_try_cast("[1]", origin) == [1]
        assert _simplistic_try_cast("[1,'str']", origin) == [1, "str"]
        assert _simplistic_try_cast("[1,2]", origin[int]) == [1, 2]

        assert _simplistic_try_cast("(1,)", origin) == (1,)
        assert _simplistic_try_cast("(1,'str')", origin) == (1, "str")
        assert _simplistic_try_cast("(1,2)", origin[int]) == (1, 2)

        with pytest.raises(CastError, match=r"Could not cast '\(1\)' to \w+"):
            _simplistic_try_cast("(1)", origin)
        with pytest.raises(CastError, match=r"Could not cast '\[1,2\]' to \w+\[str\]"):
            _simplistic_try_cast("[1,2]", origin[str])
        with pytest.raises(CastError, match=r"Could not cast '\[1,str\]' to \w+"):
            _simplistic_try_cast("[1,str]", origin)


def test_try_cast_dict():
    assert _simplistic_try_cast("{1: 2}", dict) == {1: 2}
    assert _simplistic_try_cast("{1: 2}", dict[int, int]) == {1: 2}
    assert _simplistic_try_cast("{1: '2'}", dict[int, str]) == {1: "2"}
    assert _simplistic_try_cast("{1: '2'}", dict[int, typing.Any]) == {1: "2"}

    with pytest.raises(CastError, match=r"""Could not cast "\{1: '2'\}" to dict\[int, int\]"""):
        _simplistic_try_cast("{1: '2'}", dict[int, int])
    with pytest.raises(CastError, match=r"""Could not cast "\{1: '2'\}" to dict\[str, str\]"""):
        _simplistic_try_cast("{1: '2'}", dict[str, str])
    with pytest.raises(CastError, match=r"Could not cast '\{str: str\}' to dict"):
        _simplistic_try_cast("{str: str}", dict)


def test_try_cast_callable():
    assert (
        _simplistic_try_cast(
            "chz.tiepin:_simplistic_try_cast", typing.Callable[[str, typing.Any], typing.Any]
        )
        is _simplistic_try_cast
    )

    assert (
        _simplistic_try_cast("chz.tiepin:_simplistic_try_cast", typing.Callable[..., typing.Any])
        is _simplistic_try_cast
    )

    with pytest.raises(
        CastError,
        match=r"Could not cast 'chz.tiepin:_simplistic_try_cast' to Callable\[\[int\], int\]",
    ):
        _simplistic_try_cast("chz.tiepin:_simplistic_try_cast", typing.Callable[[int], int])

    with pytest.raises(
        CastError,
        match=r"Could not cast 'does_not_exist:penguin' to Callable\[\[int\], int\]\. Could not import module.*ModuleNotFoundError",
    ):
        _simplistic_try_cast("does_not_exist:penguin", typing.Callable[[int], int])


def test_try_cast_tuple_unpack():
    # fmt: off
    assert _simplistic_try_cast("1,2,3", tuple[int, *tuple[str, int]]) == (1, "2", 3)
    assert _simplistic_try_cast("1,2,3", tuple[int, typing.Unpack[tuple[str, int]]]) == (1, "2", 3)

    assert _simplistic_try_cast("1,2,3", tuple[int, *tuple[str, ...]]) == (1, "2", "3")
    assert _simplistic_try_cast("1,2,3", tuple[int, typing.Unpack[tuple[str, ...]]]) == (1, "2", "3")

    assert _simplistic_try_cast("1,2,3,4", tuple[int, *tuple[str, ...]]) == (1, "2", "3", "4")
    assert _simplistic_try_cast("1,2,3,4", tuple[int, typing.Unpack[tuple[str, ...]]]) == (1, "2", "3", "4")

    assert _simplistic_try_cast("1,2,3,4", tuple[int, *tuple[str, ...], int, int]) == (1, "2", 3, 4)
    assert _simplistic_try_cast("1,2,3,4", tuple[int, typing.Unpack[tuple[str, ...]], int, int]) == (1, "2", 3, 4)

    assert _simplistic_try_cast("1,2,3,4", tuple[int, *tuple[str, *tuple[int, int]]]) == (1, "2", 3, 4)
    assert _simplistic_try_cast("1,2,3,4", tuple[int, typing.Unpack[tuple[str, typing.Unpack[tuple[int, int]]]]]) == (1, "2", 3, 4)
    # fmt: on

    with pytest.raises(
        CastError,
        match=re.escape(
            "Could not cast '1,2' to tuple[int, *tuple[str, int]] because of length mismatch"
        ),
    ):
        _simplistic_try_cast("1,2", tuple[int, *tuple[str, int]])


def test_try_cast_union_overlap():
    assert _simplistic_try_cast("1", str | int) == 1
    assert _simplistic_try_cast("1", int | str) == 1

    assert _simplistic_try_cast("None", str | None) == None
    assert _simplistic_try_cast("None", None | str) == None

    assert _simplistic_try_cast("all", tuple[str, ...] | typing.Literal["all"]) == "all"
    assert _simplistic_try_cast("all", typing.Literal["all"] | tuple[str, ...]) == "all"

    assert _simplistic_try_cast("None", None | typing.Literal["None"]) == "None"
    assert _simplistic_try_cast("None", typing.Literal["None"] | None) == "None"

    assert _simplistic_try_cast("None", None | tuple[str, ...]) == None
    assert _simplistic_try_cast("None", tuple[str, ...] | None) == None

    assert _simplistic_try_cast("", tuple[str, ...] | str) == ()
    assert _simplistic_try_cast("", tuple[str, ...] | typing.Literal[""]) == ""


def test_try_cast_enum():
    class Color(enum.Enum):
        RED = 1
        GREEN = 2

    assert _simplistic_try_cast("RED", Color) == Color.RED
    assert _simplistic_try_cast("GREEN", Color) == Color.GREEN
    assert _simplistic_try_cast("1", Color) == Color.RED
    assert _simplistic_try_cast("2", Color) == Color.GREEN

    with pytest.raises(CastError, match="Could not cast 'BLUE' to .*Color"):
        _simplistic_try_cast("BLUE", Color)
    with pytest.raises(CastError, match="Could not cast '3' to .*Color"):
        _simplistic_try_cast("3", Color)


def test_try_cast_fractions():
    assert _simplistic_try_cast("1/2", fractions.Fraction) == fractions.Fraction(1, 2)
    assert _simplistic_try_cast("1", fractions.Fraction) == fractions.Fraction(1)
    assert _simplistic_try_cast("1.5", fractions.Fraction) == fractions.Fraction(3, 2)


def test_try_cast_pathlib():
    assert _simplistic_try_cast("foo", pathlib.Path) == pathlib.Path("foo")


def test_approx_type_hash():
    import builtins
    from typing import Callable, Literal, TypeVar, Union

    _T = TypeVar("_T")

    assert approx_type_hash(int)[:8] == "46f8ab7c"

    assert approx_type_hash(str)[:8] == "3442496b"
    assert approx_type_hash("str")[:8] == "3442496b"
    assert approx_type_hash(builtins.str)[:8] == "3442496b"

    class float: ...

    assert approx_type_hash(builtins.float)[:8] == "685e8036"
    assert approx_type_hash(float)[:8] == "685e8036"  # can't tell the difference...
    assert approx_type_hash("float")[:8] == "685e8036"

    assert approx_type_hash(list[int])[:8] == "e4c2cba0"
    assert approx_type_hash("list[int]")[:8] == "e4c2cba0"
    assert approx_type_hash(list["int"])[:8] == "e4c2cba0"

    assert approx_type_hash(list[_T])[:8] == "c6eb1529"

    assert approx_type_hash(Union[int, str])[:8] == "c1729268"
    assert approx_type_hash(Union[str, int])[:8] == "d811461d"
    assert approx_type_hash(Union[str, "int"])[:8] == "d811461d"

    assert approx_type_hash(Callable[[int], str])[:8] == "0dc453ef"
    assert approx_type_hash(Literal[1, "asdf", False])[:8] == "ee5b7e0f"


def test_simplistic_type_of_value():
    tov = _simplistic_type_of_value

    assert tov(1) is int
    assert tov("foo") is str

    assert tov([1, 2, 3]) == list[int]
    assert tov([1, 2, 3.0]) == list[int | float]
    assert tov([1, 2, "3"]) == list[int | str]

    assert tov((1, 2, 3)) == tuple[int, int, int]
    assert tov((1, 2, 3.0)) == tuple[int, int, float]
    assert tov((1, "2", 3.0)) == tuple[int, str, float]
    assert tov(tuple(i for i in range(12))) == tuple[int, ...]

    assert tov([(1, 2), (3, 4)]) == list[tuple[int, int]]
    assert tov([(1, 2), (3, 4, 5)]) == list[tuple[int, int] | tuple[int, int, int]]

    assert tov({1: "a", "b": 2}) == dict[int | str, str | int]

    assert tov(int) == type[int]

    class A: ...

    class B(A): ...

    class C(A): ...

    assert tov([A(), B()]) == list[A]
    assert tov([B(), A()]) == list[A]
    assert tov([B(), C()]) == list[B | C]
