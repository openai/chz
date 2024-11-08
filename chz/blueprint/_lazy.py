from typing import AbstractSet, Any, Callable, TypeVar

from chz.blueprint._entrypoint import InvalidBlueprintArg
from chz.blueprint._wildcard import wildcard_key_approx, wildcard_key_to_regex
from chz.tiepin import type_repr

T = TypeVar("T")


class Evaluatable: ...


class Value(Evaluatable):
    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Value({self.value})"


class ParamRef(Evaluatable):
    def __init__(self, ref: str) -> None:
        self.ref = ref

    def __repr__(self) -> str:
        return f"ParamRef({self.ref})"


class Thunk(Evaluatable):
    def __init__(self, fn: Callable[..., Any], kwargs: dict[str, ParamRef]) -> None:
        self.fn = fn
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return f"Thunk({type_repr(self.fn)}, {self.kwargs})"


def evaluate(value_mapping: dict[str, Evaluatable]) -> Any:
    assert "" in value_mapping

    # TODO: guard against infinite recursion

    def inner(ref: str) -> Any:
        value = value_mapping[ref]
        assert isinstance(value, Evaluatable)

        if isinstance(value, Value):
            return value.value

        if isinstance(value, ParamRef):
            try:
                ret = inner(value.ref)
            except Exception as e:
                e.add_note(f" (when dereferencing {ref!r})")
                raise
            assert not isinstance(ret, Evaluatable)
            value_mapping[ref] = Value(ret)
            return ret

        if isinstance(value, Thunk):
            kwargs = {}
            for k, v in value.kwargs.items():
                assert isinstance(v, ParamRef)
                try:
                    kwargs[k] = inner(v.ref)
                except Exception as e:
                    e.add_note(f" (when evaluating argument {k!r} for {type_repr(value.fn)})")
                    raise
            ret = value.fn(**kwargs)
            return ret

        raise AssertionError

    return inner("")


def check_reference_targets(
    value_mapping: dict[str, Evaluatable], param_paths: AbstractSet[str]
) -> None:
    for param_path, value in value_mapping.items():
        if isinstance(value, ParamRef):
            if value.ref not in param_paths:
                ratios = {p: wildcard_key_approx(value.ref, p) for p in param_paths}
                extra = ""
                if ratios:
                    max_option = max(ratios, key=lambda v: ratios[v][0])
                    if ratios[max_option][0] > 0.1:
                        extra = f"\nDid you mean {ratios[max_option][1]!r}?"

                nested_pattern = wildcard_key_to_regex("..." + value.ref)
                found_key = next((p for p in param_paths if nested_pattern.fullmatch(p)), None)
                if found_key is not None:
                    extra += f"\nDid you get the nesting wrong, maybe you meant {found_key!r}?"

                raise InvalidBlueprintArg(
                    f"Invalid reference target {value.ref!r} for {param_path}" + extra
                )