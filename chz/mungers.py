from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar, overload

if TYPE_CHECKING:
    from frozendict import frozendict

    from chz.field import Field


_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")


class Munger:
    """Marker class for mungers"""

    def __call__(self, value: Any, *, chzself: Any = None, field: Field | None = None) -> Any:
        raise NotImplementedError


class if_none(Munger):
    """If None, munge the field to the result of an arbitrary function of the chz object."""

    def __init__(self, replacement: Callable[[Any], Any]):
        self.replacement = replacement

    def __call__(self, value: _T | None, *, chzself: Any = None, field: Field | None = None) -> _T:
        if value is not None:
            return value
        return self.replacement(chzself)


class attr_if_none(Munger):
    """If None, munge the field to another attribute of the chz object."""

    def __init__(self, replacement_attr: str):
        self.replacement_attr = replacement_attr

    def __call__(self, value: _T | None, *, chzself: Any = None, field: Field | None = None) -> _T:
        if value is not None:
            return value
        return getattr(chzself, self.replacement_attr)


class default_munger(Munger):
    def __init__(self, fn: Callable[[Any, Any], Any]):
        self.fn = fn

    def __call__(self, value: Any, *, chzself: Any = None, field: Field | None = None) -> Any:
        # Note: when the munger arg is a function, it is called as munger(chzself, value),
        # and we keep that calling convention here. See also the comment in Field.__init__.
        return self.fn(chzself, value)


class freeze_dict(Munger):
    """Freezes a dictionary value so the object is hashable."""

    @overload
    def __call__(
        self, value: Mapping[_K, _V], *, chzself: Any = None, field: Field | None = None
    ) -> frozendict[_K, _V]: ...

    @overload
    def __call__(
        self, value: Mapping[_K, _V] | None, *, chzself: Any = None, field: Field | None = None
    ) -> frozendict[_K, _V] | None: ...

    def __call__(
        self, value: Mapping[_K, _V] | None, *, chzself: Any = None, field: Field | None = None
    ) -> frozendict[_K, _V] | None:
        from frozendict import frozendict

        if value is not None and not isinstance(value, frozendict):
            return frozendict[_K, _V](value)  # pyright: ignore[reportUnknownArgumentType]
        return value
