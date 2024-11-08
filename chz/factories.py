import ast
import collections
import functools
import importlib
import re
import sys
import types
import typing
from typing import Any, Callable, Union, get_args, get_origin

import typing_extensions

from chz.tiepin import (
    CastError,
    InstantiableType,
    TypeForm,
    _simplistic_try_cast,
    eval_in_context,
    is_instantiable_type,
    is_subtype,
    is_subtype_instance,
    is_union_type,
    type_repr,
)
from chz.util import _MISSING_TYPE, MISSING


class MetaFromString(Exception): ...


class MetaFactory:
    """
    A metafactory represents a set of possible factories, where a factory is a callable that can
    give us a value of a given type.

    This is the heart of polymorphic construction in chz. The idea is that when instantiating
    Blueprints, you should be able to not only specify the arguments to whatever is being
    constructed, but also specify what the thing to be constructed is!

    In other words, when constructing a value, chz lets you specify the factory to produce it,
    in addition to the arguments to pass to that factory.

    In other other words, many tools will let you construct an X by specifying `...` to feed to
    `X(...)`. But chz lets you construct an X by specifying both callee and arguments in `...(...)`

    This concept is a little tricky, but it's fairly intuitive when you actually use it.
    Consider looking at the docstring for `subclass` for a concrete example.
    """

    def unspecified_factory(self) -> Callable[..., Any] | None:
        """The default callable to use to get a value of the expected type.

        If this returns None, there is no default. In order to construct a value of the expected
        type, the user must explicitly specify a factory.
        """
        raise NotImplementedError

    def from_string(self, factory: str) -> Callable[..., Any]:
        """The callable that best corresponds to `factory`."""
        raise NotImplementedError

    def perform_cast(self, value: str, default_target: TypeForm):
        """
        TODO: maybe make this default to:
        return _simplistic_try_cast(value, default_target)
        """
        raise NotImplementedError


class subclass(MetaFactory):
    """
    Read the docstring for MetaFactory first.

    ```
    @chz.chz
    class Experiment:
        model: Model
    ```

    In the above example, we want to construct a value for the model for our experiment.
    How should we go about making a model?

    The meta_factory we provide is what is meant to answer this question. And in this case, the
    answer we want is: we should make a model by attempting to instantiate `Model` or some subclass
    of `Model`.

    This is a common enough answer that chz in fact defaults to it. That is, here chz will
    set the meta_factory to be `subclass(base_cls=Model, default_cls=Model)` for our model field.
    See the logic in chz.Field.

    Given `model=Transformer model.n_layers=16 model.d_model=1024`
    chz will construct `Transformer(n_layers=16, d_model=1024`

    That is, if the user specifies a factory for the model field, e.g. model="Transformer", then
    the logic in `subclass.from_string` will attempt to find a subclass of `Model` (the `base_cls`)
    named `Transformer` and instantiate it.

    Given `model.n_layers=16 model.d_model=1024`
    chz will construct `Model(n_layers=Y, d_model=Z)`

    That is, if the user doesn't specify a factory (maybe they only specify subcomponents, like
    `model.n_layers=16`), then we will default to trying to instantiate `Model` (the `default_cls`).
    """

    def __init__(
        self, base_cls: InstantiableType, default_cls: InstantiableType | None = None
    ) -> None:
        self.base_cls = base_cls
        self.default_cls = default_cls if default_cls is not None else base_cls

    def unspecified_factory(self) -> Callable[..., Any]:
        return self.default_cls  # type: ignore[return-value]

    def from_string(self, factory: str) -> Callable[..., Any]:
        """
        If factory=module:cls, import module and return cls.
        If factory=cls, do our best to find a subclass of base_cls named cls.
        """
        return _find_subclass(factory, self.base_cls)

    def perform_cast(self, value: str, default_target: TypeForm):
        if self.default_cls is not None:
            try:
                return _simplistic_try_cast(value, self.default_cls)
            except CastError:
                pass
        return _simplistic_try_cast(value, self.base_cls)


class _sentinel:
    pass


class function(MetaFactory):
    def __init__(
        self,
        unspecified: Callable[..., Any] | None = None,
        *,
        default_module: str | types.ModuleType | None | _sentinel = _sentinel(),  # noqa: B008
    ) -> None:
        """
        Read the docstring for `MetaFactory` and `subclass` first.

        If you specify `function` as your meta_factory, any function can serve as a factory to
        construct a value of the expected type.

        ```
        def wikipedia_text(seed: int) -> Dataset: ...

        @chz.chz
        class Experiment:
            dataset: Dataset = field(meta_factory=function())
        ```

        In the above example, we want to construct a value of type `Dataset` for our experiment.
        The way we want to do this is by calling some function that returns a `Dataset`.

        Given `dataset=wikipedia_text dataset.seed=217`
        chz will construct `wikipedia_text(seed=217)`.

        If you use a fully qualified name like `function=module:fn` it's obvious where to find the
        function. Otherwise, chz looks for an appropriately named function in the module
        `default_module` (which defaults to the module in which the chz class was defined).

        If you love `wikipedia_text` and you don't wish to explicitly specify
        `dataset=wikipedia_text` every time, set the `unspecified` argument to be `wikipedia_text`.
        This way, chz will default to trying to call `wikipedia_text` to instantiate a value of type
        `Dataset`, instead of erroring because it doesn't know what factory to use to produce a
        Dataset.
        """
        self.unspecified = unspecified
        if isinstance(default_module, _sentinel):
            # TODO: replace with _getframemodulename in Python 3.12
            default_module = sys._getframe(1).f_globals["__name__"]
        assert not isinstance(default_module, _sentinel)
        self.default_module = default_module

    def unspecified_factory(self) -> Callable[..., Any] | None:
        return self.unspecified

    def from_string(self, factory: str) -> Callable[..., Any]:
        """
        If factory=module:fn, import module and return fn.
        If factory=fn, look in the default module for a function named fn.
        """
        if ":" not in factory:
            if self.default_module is None:
                raise MetaFromString(
                    f"No module specified in {factory!r} and no default module specified"
                )
            if isinstance(self.default_module, str):
                module = importlib.import_module(self.default_module)
            else:
                module = self.default_module
            var = factory
        else:
            module_name, var = factory.split(":", 1)
            if module_name != "lambda" and not module_name.startswith("lambda "):
                module = _module_from_name(module_name)
            else:
                import ast

                if isinstance(self.default_module, str):
                    eval_ctx = importlib.import_module(self.default_module)
                elif self.default_module is not None:
                    eval_ctx = self.default_module
                else:
                    eval_ctx = None

                try:
                    # TODO: add docs for this branch
                    if isinstance(ast.parse(factory).body[0].value, ast.Lambda):  # type: ignore[attr-defined]
                        return eval_in_context(factory, eval_ctx)
                except Exception as e:
                    raise MetaFromString(
                        f"Could not interpret {factory!r} as a function: {e}"
                    ) from None
                raise AssertionError

        return _module_getattr(module, var)

    def perform_cast(self, value: str, default_target: TypeForm):
        return _simplistic_try_cast(value, default_target)


class union(MetaFactory):
    def __init__(
        self, type_args: tuple[InstantiableType, ...], default_cls: InstantiableType | None = None
    ) -> None:
        self.type_args = type_args

        self.default_cls = default_cls
        if default_cls is None:
            if self.type_args and len(self.type_args) == 2 and type(None) in self.type_args:
                unwrapped_optional = [t for t in self.type_args if t is not type(None)][0]
                if callable(unwrapped_optional):
                    self.default_cls = unwrapped_optional

    def unspecified_factory(self) -> Callable[..., Any] | None:
        return self.default_cls  # type: ignore[return-value]

    def from_string(self, factory: str) -> Callable[..., Any]:
        if is_instantiable_type(self.default_cls):
            return subclass(self.default_cls).from_string(factory)

        for t in self.type_args:
            if factory == t.__name__ and is_instantiable_type(t):
                return subclass(t).from_string(factory)
        raise MetaFromString(f"Could not produce a union instance from {factory!r}")

    def perform_cast(self, value: str, default_target: TypeForm):
        # It's important that we do not try to cast to just self.unwrapped_optional, since this
        # means we will cast "None" incorrectly
        return _simplistic_try_cast(value, Union[*self.type_args])


class type_subclass(MetaFactory):
    def __init__(self, base_type: type, default_type: InstantiableType | None = None) -> None:
        assert get_origin(base_type) is type
        base_type = get_args(base_type)[0]
        assert isinstance(base_type, type)
        if default_type is not None:
            default_type = get_args(default_type)[0]
        else:
            default_type = base_type
        assert isinstance(default_type, type)

        self.base_type = base_type
        self.default_type = default_type

    def unspecified_factory(self) -> Callable[..., Any]:
        return lambda: self.default_type

    def from_string(self, factory: str) -> Callable[..., Any]:
        """
        If factory=module:cls, import module and return cls.
        If factory=cls, do our best to find a subclass of base_cls named cls.
        """
        typ = subclass(self.base_type, self.default_type).from_string(factory)
        return lambda: typ

    def perform_cast(self, value: str, default_target: TypeForm):
        if self.default_type is not None:
            try:
                return _simplistic_try_cast(value, type[self.default_type])
            except CastError:
                pass
        return _simplistic_try_cast(value, type[self.base_type])


def _module_from_name(name: str) -> types.ModuleType:
    try:
        return importlib.import_module(name)
    except ImportError as e:
        raise MetaFromString(f"Could not import module {name!r} ({type(e).__name__}: {e}") from None


def _module_getattr(mod: types.ModuleType, attr: str) -> Any:
    try:
        for a in attr.split("."):
            mod = getattr(mod, a)
        return mod
    except AttributeError:
        raise MetaFromString(f"No attribute named {attr!r} in module {mod.__name__}") from None


def _find_subclass(spec: str, superclass: TypeForm):
    module_name = None
    if ":" in spec:
        module_name, var = spec.split(":", 1)
    else:
        var = spec

    match = re.fullmatch(r"(?P<base>[^\s\[\]]+)(\[(?P<generic>.+)\])?", var)
    if match is None:
        raise MetaFromString(f"Failed to parse '{spec}' as a class name")
    base = match.group("base")
    generic = match.group("generic")

    if module_name is None and not base.isidentifier():
        if "." in base:
            module_name, base = base.rsplit(".", 1)
        if not base.isidentifier():
            raise MetaFromString(
                f"No subclass of {type_repr(superclass)} named {base!r} (invalid identifier)"
            )

    if module_name is not None:
        module = _module_from_name(module_name)
        # TODO: think about this type ignore
        return _maybe_generic(_module_getattr(module, base), generic, template=superclass)  # type: ignore[arg-type]

    visited_subclasses = set()
    base_class_origin = getattr(superclass, "__origin__", superclass)

    if not is_instantiable_type(base_class_origin) or base_class_origin in {
        object,
        typing.Any,
        typing_extensions.Any,
    }:
        raise MetaFromString(
            f"Could not find {spec!r}, try a fully qualified name e.g. module_name:{spec}"
        )
    assert base_class_origin is not type

    all_subclasses = collections.deque(base_class_origin.__subclasses__())
    all_subclasses.appendleft(superclass)
    while all_subclasses:
        cls = all_subclasses.popleft()
        if cls in visited_subclasses:
            continue
        visited_subclasses.add(cls)
        if cls.__name__ == base:
            assert module_name is None
            return _maybe_generic(cls, generic, template=superclass)  # type: ignore[arg-type]
        cls_origin = getattr(cls, "__origin__", cls)
        assert cls_origin is not type
        all_subclasses.extend(cls_origin.__subclasses__())
    raise MetaFromString(f"No subclass of {type_repr(superclass)} named {base!r}")


def _maybe_generic(
    cls: type, generic: str | None, template: InstantiableType
) -> Callable[..., Any]:
    if generic is None:
        return cls

    assert isinstance(generic, str)
    generic_args_str = generic.split(",")
    args: list[object] = []
    for i, arg_str in enumerate(generic_args_str):
        arg_str = arg_str.strip()
        if ":" in arg_str:
            module_name, arg = arg_str.split(":", 1)
            args.append(_module_getattr(_module_from_name(module_name), arg))
        elif arg_str == "...":
            args.append(...)
        else:
            # TODO: note this assumes covariance, also give a better error
            superclass = template.__args__[i]  # type: ignore[union-attr]
            args.append(_find_subclass(arg_str, superclass))

    origin: Any = getattr(cls, "__origin__", cls)
    return origin[*args]


def _return_prospective(obj: Any, annotation: TypeForm, factory: str) -> Any:
    if annotation not in {
        object,
        typing.Any,
        typing_extensions.Any,
    }:
        if is_subtype_instance(obj, annotation):
            # Allow things to be instances!
            return lambda: obj
    elif not callable(obj):
        # ...including if we would just error on the next line
        return lambda: obj

    if not callable(obj):
        raise MetaFromString(f"Expected {obj} from {factory!r} to be callable")
    if isinstance(obj, type) and not is_subtype(obj, annotation):
        raise MetaFromString(
            f"Expected {type_repr(obj)} from {factory!r} to be a subtype of {type_repr(annotation)}"
        )
    return obj


def get_unspecified_from_annotation(annotation: TypeForm) -> Callable[..., Any] | None:

    if typing.get_origin(annotation) is type:
        base_type = typing.get_args(annotation)[0]
        assert isinstance(base_type, type)
        return type[base_type]  # type: ignore[return-value]

    if is_union_type(annotation):
        type_args = typing.get_args(annotation)
        if type_args and len(type_args) == 2 and type(None) in type_args:
            unwrapped_optional = [t for t in type_args if t is not type(None)][0]
            if callable(unwrapped_optional):
                return unwrapped_optional
        return None

    if is_instantiable_type(annotation):
        return annotation  # type: ignore[return-value]

    if annotation is None:
        return lambda: None

    # Probably a special form
    return None


class standard(MetaFactory):
    def __init__(
        self,
        annotation: TypeForm,
        unspecified: Callable[..., Any] | None = None,
        default_module: str | types.ModuleType | None | _MISSING_TYPE = MISSING,
    ) -> None:

        self.annotation = annotation
        self.original_unspecified = unspecified
        self._default_module = default_module

    @functools.cached_property
    def computed_unspecified(self) -> Callable[..., Any] | None:
        return (
            get_unspecified_from_annotation(self.annotation)
            if self.original_unspecified is None
            else self.original_unspecified
        )

    @property
    def default_module(self) -> types.ModuleType | _MISSING_TYPE | None:
        if isinstance(self._default_module, str):
            return _module_from_name(self._default_module)
        return self._default_module

    def unspecified_factory(self) -> Callable[..., Any] | None:

        if (
            self.computed_unspecified is not None
            and typing.get_origin(self.annotation) is type
            and typing.get_origin(self.computed_unspecified) is type
        ):
            base_type = typing.get_args(self.computed_unspecified)[0]
            # TODO: remove special handling here and elsewhere by moving logic to collect_params
            return lambda: base_type

        return self.computed_unspecified

    def from_string(self, factory: str) -> Callable[..., Any]:

        if ":" in factory:
            module_name, var = factory.split(":", 1)

            # fun lambda case
            # TODO: add docs for fun lambda case
            if module_name == "lambda" or module_name.startswith("lambda "):

                default_module = self.default_module
                if isinstance(default_module, _MISSING_TYPE) or default_module is None:
                    eval_ctx = None
                else:
                    eval_ctx = default_module

                try:
                    if isinstance(ast.parse(factory).body[0].value, ast.Lambda):  # type: ignore[attr-defined]
                        return eval_in_context(factory, eval_ctx)
                except Exception as e:
                    raise MetaFromString(
                        f"Could not interpret {factory!r} as a function: {e}"
                    ) from None
                raise AssertionError

            # we've just got something explicitly specified
            module = _module_from_name(module_name)

            match = re.fullmatch(r"(?P<base>[^\s\[\]]+)(\[(?P<generic>.+)\])?", var)
            if match is None:
                raise MetaFromString(f"Failed to parse {factory!r} as a class name")
            base = match.group("base")
            generic = match.group("generic")

            # TODO: think about this type ignore
            typ = _maybe_generic(_module_getattr(module, base), generic, template=self.annotation)  # type: ignore[arg-type]
            return _return_prospective(typ, self.annotation, factory=factory)

        try:

            if self.annotation in {object, typing.Any, typing_extensions.Any}:
                return _find_subclass(factory, self.annotation)

            if typing.get_origin(self.annotation) is type:
                base_type = typing.get_args(self.annotation)[0]
                assert isinstance(base_type, type)
                typ = _find_subclass(factory, base_type)
                return lambda: typ

            if is_union_type(self.annotation):
                if self.original_unspecified is not None:
                    try:
                        if is_instantiable_type(self.original_unspecified):
                            return _find_subclass(factory, self.original_unspecified)
                    except MetaFromString:
                        pass
                for t in typing.get_args(self.annotation):
                    try:
                        if is_instantiable_type(t):
                            return _find_subclass(factory, t)
                    except MetaFromString:
                        pass
                if type(None) in typing.get_args(self.annotation) and factory == "None":
                    return lambda: None
                raise MetaFromString(f"Could not produce a union instance from {factory!r}")

            if is_instantiable_type(self.annotation):
                return _find_subclass(factory, self.annotation)

            if self.annotation is None and factory == "None":
                return lambda: None

        except MetaFromString as e:

            try:
                default_module = self.default_module
                if default_module is not None and not isinstance(default_module, _MISSING_TYPE):
                    obj = _module_getattr(default_module, factory)
                    return _return_prospective(obj, self.annotation, factory=factory)

            except MetaFromString:
                pass

            raise e

        # Probably a special form
        raise MetaFromString(
            f"Could not produce a {type_repr(self.annotation)} instance from {factory!r}"
        )

    def perform_cast(self, value: str, default_target: TypeForm):
        if self.original_unspecified is not None:
            try:
                return _simplistic_try_cast(value, self.original_unspecified)
            except CastError:
                pass
        return _simplistic_try_cast(value, self.annotation)
