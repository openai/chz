from __future__ import annotations

import itertools
import types
from typing import Any, Sequence, TypeVar

import chz.blueprint
from chz.blueprint._argmap import Layer
from chz.blueprint._wildcard import wildcard_key_to_regex
from chz.tiepin import type_repr

_T = TypeVar("_T")


def argv_to_blueprint_args(
    argv: list[str], *, allow_hyphens: bool = False
) -> dict[str, chz.blueprint.Castable | chz.blueprint.Reference]:
    # TODO: allow stuff like model[family=linear n_layers=1]
    ret: dict[str, chz.blueprint.Castable | chz.blueprint.Reference] = {}
    for arg in argv:
        try:
            key, value = arg.split("=", 1)
        except ValueError:
            raise ValueError(
                f"Invalid argument {arg!r}. Specify arguments in the form key=value"
            ) from None
        if allow_hyphens:
            key = key.lstrip("-")

        # parse key@=reference syntax (note =@ would be ambiguous)
        if key.endswith("@"):
            ret[key.removesuffix("@")] = chz.blueprint.Reference(value)
        else:
            ret[key] = chz.blueprint.Castable(value)
    return ret


def beta_argv_arg_to_string(key: str, value: Any) -> str:
    if isinstance(value, chz.blueprint.Castable):
        return f"{key}={value.value}"
    if isinstance(value, chz.blueprint.Reference):
        return f"{key}@={value.ref}"
    if isinstance(value, (types.FunctionType, type)):
        return f"{key}={type_repr(value)}"
    if isinstance(value, str):
        return f"{key}={value}"
    if isinstance(value, (int, float, bool)) or value is None:
        return f"{key}={repr(value)}"
    # Probably safe to use repr here, but I'm curious to see how people end up using this
    raise NotImplementedError(
        f"TODO: beta_blueprint_to_argv does not currently convert {value!r} of "
        f"type {type(value)} to string"
    )


def beta_blueprint_to_argv(blueprint: chz.Blueprint[_T]) -> list[str]:
    """Returns a list of arguments that would recreate the given blueprint.

    Please do not use this function without asking @shantanu, it is slow and not fully robust,
    and more importantly, there may well be a better way to accomplish your goal.
    """
    return [beta_argv_arg_to_string(key, value) for key, value in _collapse_layers(blueprint)]


def _collapse_layer(ordered_args: Sequence[tuple[str, Any]], layer: Layer) -> list[tuple[str, Any]]:
    """Collapses `layer` into `ordered_args`, overriding any old keys as necessary."""

    layer_args: list[tuple[str, Any]] = []
    keys_to_remove: set[str] = set()

    previous_keys = {prev_key for prev_key, _ in ordered_args}

    for key, value in itertools.chain(layer.qualified.items(), layer.wildcard.items()):
        # Remove any previous args that would be overwritten by this one.
        wildcard = wildcard_key_to_regex(key) if "..." in key else None

        if wildcard:
            for prev_key, _ in ordered_args:
                # TODO(shantanu): usually this regex is only matched against concrete keys
                # However, here we're matching against other wildcards
                if wildcard.fullmatch(prev_key):
                    keys_to_remove.add(prev_key)
        else:
            if key in previous_keys:
                keys_to_remove.add(key)
        layer_args.append((key, value))

    # Commit the new layer.
    return [arg for arg in ordered_args if arg[0] not in keys_to_remove] + layer_args


def _collapse_layers(blueprint: chz.Blueprint[_T]) -> list[tuple[str, Any]]:
    """Collapses the layers of a blueprint into a list of key-value pairs.

    These could be applied as a single layer to a new blueprint to recreate the original.
    """
    ordered_args: list[tuple[str, Any]] = []
    for layer in blueprint._arg_map._layers:
        ordered_args = _collapse_layer(ordered_args, layer)
    return ordered_args
