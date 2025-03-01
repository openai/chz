from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import AbstractSet, Any, Iterator, Mapping

from chz.blueprint._entrypoint import ExtraneousBlueprintArg
from chz.blueprint._wildcard import wildcard_key_approx, wildcard_key_to_regex


class Layer:
    def __init__(self, params: Mapping[str, Any], layer_name: str | None):
        self._params = params
        self.layer_name = layer_name

        self.qualified = {}
        self.wildcard = {}
        self._to_regex = {}
        # Match more specific wildcards first
        for k, v in sorted(params.items(), key=lambda kv: -len(kv[0])):
            if "..." in k:
                self.wildcard[k] = v
                self._to_regex[k] = wildcard_key_to_regex(k)
            else:
                self.qualified[k] = v

        self.qualified_sorted = sorted(self.qualified.keys())

    def get_kv(self, exact_key: str) -> tuple[str, Any] | None:
        if exact_key in self.qualified:
            return exact_key, self.qualified[exact_key]
        for wildcard_key, value in self.wildcard.items():
            if self._to_regex[wildcard_key].fullmatch(exact_key):
                return wildcard_key, value
        return None

    def iter_keys(self) -> Iterator[tuple[str, bool]]:
        yield from ((k, False) for k in self.qualified)
        yield from ((k, True) for k in self.wildcard)

    def nest_subpath(self, subpath: str | None) -> Layer:
        if subpath is None:
            return self
        return Layer(
            {join_arg_path(subpath, k): v for k, v in self._params.items()}, self.layer_name
        )

    def __repr__(self) -> str:
        return f"<Layer {self.layer_name} {self.qualified | self.wildcard}>"


@dataclass(frozen=True)
class _FoundArgument:
    key: str
    value: Any
    layer_index: int
    layer_name: str | None


def _valid_parent(parts: list[str], param_paths: AbstractSet[str]) -> str | None:
    for i in reversed(range(1, len(parts))):
        parent = ".".join(parts[:i])
        if parent in param_paths:
            return parent
    return None


class ArgumentMap:
    def __init__(self, layers: list[Layer]) -> None:
        self._layers = layers

    def add_layer(self, layer: Layer) -> None:
        self._layers.append(layer)

    def subpaths(self, path: str, strict: bool = False) -> list[str]:
        """Returns the suffix of arguments this contains that would match a subpath of path.

        The invariant is that for each element `suffix` in the returned list, `path + suffix`
        would match an argument in this map.

        Args:
            strict: Whether to avoid returning arguments that match path exactly.
        """
        assert not path.endswith(".")

        wildcard_literal = path.split(".")[-1]
        # assert wildcard_literal
        assert path.endswith(wildcard_literal)

        path_plus_dot = path + "."

        ret = []
        for layer in self._layers:
            if not strict and path in layer.qualified:
                ret.append("")

            if not path:
                ret.extend([k for k in layer.qualified_sorted if k])
            else:
                index = bisect.bisect_left(layer.qualified_sorted, path_plus_dot)
                for i in range(index, len(layer.qualified_sorted)):
                    key = layer.qualified_sorted[i]
                    if not key.startswith(path_plus_dot):
                        break
                    ret.append(key.removeprefix(path_plus_dot))
                    assert key == join_arg_path(path, ret[-1])

            for key in layer.wildcard:
                # If it's not a wildcard, the logic is straightforward. But doing the equivalent
                # for wildcards is tricky!
                i = key.rfind(wildcard_literal)
                if i == -1:
                    continue
                # The not strict case is not complicated, we just regex match
                if layer._to_regex[key].fullmatch(path):
                    if not strict:
                        ret.append("")
                        assert layer._to_regex[key].fullmatch(path + ret[-1])
                    continue
                # This needs a little thinking about.
                # Say path is "foo.bar" and key is "...bar...baz"
                # Then wildcard_literal is "bar" and we check if "...bar" matches "foo.bar"
                # Since it does, we append "...baz"
                if (
                    i + len(wildcard_literal) < len(key)
                    and key[i + len(wildcard_literal)] == "."
                    and wildcard_key_to_regex(key[: i + len(wildcard_literal)]).fullmatch(path)
                ):
                    assert i == 0 or key[i - 1] == "."
                    ret.append(key[i + len(wildcard_literal) + 1 :])
                    assert layer._to_regex[key].fullmatch(join_arg_path(path, ret[-1]))
        return ret

    def get_kv(self, exact_key: str) -> _FoundArgument | None:
        for index in reversed(range(len(self._layers))):
            layer = self._layers[index]
            if kv := layer.get_kv(exact_key):
                return _FoundArgument(kv[0], kv[1], index, layer.layer_name)
        return None

    def check_extraneous(
        self,
        used_args: set[tuple[str, int]],
        param_paths: AbstractSet[str],
        *,
        entrypoint_repr: str,
    ) -> None:
        for index in range(len(self._layers)):
            layer = self._layers[index]
            for key, is_wildcard in layer.iter_keys():
                # If something is not in used_args, it means it was either extraneous or it got
                # clobbered because something in a higher layer matched it
                if (key, index) in used_args:
                    continue

                if (
                    # It's easy to check if a non-wildcard arg was clobbered. We just check if
                    # there was a param with that name (that we should have matched if not for
                    # presumed clobbering)
                    (not is_wildcard and key not in param_paths)
                    # For wildcards, we need to match against all param paths
                    or (
                        is_wildcard
                        and not any(layer._to_regex[key].fullmatch(p) for p in param_paths)
                    )
                ):
                    # Okay, we have an extraneous argument. We're going to error, but we should
                    # helpfully try to figure out what the user wanted
                    extra = ""
                    if layer.layer_name:
                        extra += f" (from {layer.layer_name})"

                    ratios = {p: wildcard_key_approx(key, p) for p in param_paths}
                    if ratios:
                        max_option = max(ratios, key=lambda v: ratios[v][0])
                        if ratios[max_option][0] > 0.1:
                            extra = f"\nDid you mean {ratios[max_option][1]!r}?"
                    if not is_wildcard:
                        nested_pattern = wildcard_key_to_regex("..." + key)
                        found_key = next(
                            (p for p in param_paths if nested_pattern.fullmatch(p)), None
                        )
                        if found_key is not None:
                            extra += (
                                f"\nDid you get the nesting wrong, maybe you meant {found_key!r}?"
                            )
                    if key.startswith("--"):
                        extra += "\nDid you mean to use allow_hyphens=True in your entrypoint?"

                    if not is_wildcard:
                        parts = key.split(".")
                        if len(parts) >= 2:
                            valid_parent = _valid_parent(parts, param_paths)
                            if valid_parent is None:
                                extra += f"\nNo param found matching {parts[0]!r}"
                            elif valid_parent != ".".join(parts[:-1]):
                                extra += f"\nParam {valid_parent!r} is closest valid ancestor"

                    raise ExtraneousBlueprintArg(
                        f"Extraneous argument {key!r} to Blueprint for {entrypoint_repr}"
                        + extra
                        + "\nAppend --help to your command to see valid arguments"
                    )

    def __repr__(self) -> str:
        return "ArgumentMap(\n" + "\n".join("    " + repr(layer) for layer in self._layers) + "\n)"


def join_arg_path(parent: str, child: str) -> str:
    if not parent:
        return child
    if child.startswith(".") or child == "":
        return parent + child
    return parent + "." + child
