from __future__ import annotations

from dataclasses import dataclass
from typing import AbstractSet, Any, Callable, Iterator, Mapping

from chz.blueprint._entrypoint import ExtraneousBlueprintArg
from chz.blueprint._wildcard import wildcard_key_approx, wildcard_key_to_regex
from chz.tiepin import type_repr


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

    def __repr__(self) -> str:
        return f"<Layer {self.layer_name} {self.qualified | self.wildcard}>"

    def __hash__(self) -> int:
        return hash((frozenset(self._params.items()), self.layer_name))


@dataclass(frozen=True)
class _FoundArgument:
    key: str
    value: Any
    layer_index: int
    layer_name: str | None


def _valid_parent(key: str, param_paths: AbstractSet[str]) -> str | None:
    parts = key.split(".")
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

        wildcard_literal = ".".join(path.split(".")[-1:])
        assert wildcard_literal
        assert path.endswith(wildcard_literal)

        ret = []
        for layer in self._layers:
            for key, is_wildcard in layer.iter_keys():
                if is_wildcard:
                    # If it's not a wildcard, the logic is straightforward. But doing the equivalent
                    # for wildcards is tricky!
                    i = key.rfind(wildcard_literal)
                    if i == -1:
                        continue
                    # This is not too complicated:
                    if wildcard_key_to_regex(key).fullmatch(path):
                        if not strict:
                            ret.append("")
                            assert wildcard_key_to_regex(key).fullmatch(path + ret[-1])
                        continue
                    # This needs a little thinking about:
                    if (
                        i + len(wildcard_literal) < len(key)
                        and key[i + len(wildcard_literal)] == "."
                        and wildcard_key_to_regex(key[: i + len(wildcard_literal)]).fullmatch(path)
                    ):
                        ret.append(key[i + len(wildcard_literal) :])
                        assert wildcard_key_to_regex(key).fullmatch(path + ret[-1])
                else:
                    if key == path:
                        if not strict:
                            ret.append("")
                            assert key == path + ret[-1]
                        continue
                    if key.startswith(path + "."):
                        ret.append(key.removeprefix(path))
                        assert key == path + ret[-1]
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
        target: Callable[..., Any],
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
                    ratios = {p: wildcard_key_approx(key, p) for p in param_paths}
                    extra = ""
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

                    valid_parent_help = ""
                    if not is_wildcard:
                        valid_parent = _valid_parent(key, param_paths)
                        if valid_parent:
                            valid_parent_help = f" (parent key {valid_parent!r} is valid)"

                    raise ExtraneousBlueprintArg(
                        f"Extraneous argument {key!r} to Blueprint for {type_repr(target)}"
                        + extra
                        + "\nAppend --help to your command to see valid arguments"
                        + valid_parent_help
                    )

    def __repr__(self) -> str:
        return "ArgumentMap(\n" + "\n".join("    " + repr(layer) for layer in self._layers) + "\n)"