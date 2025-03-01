## Blueprints and partial application

`chz` has a `Blueprint` mechanism that powers the command line functionality. `chz.entrypoint` is
just a thin wrapper around `Blueprint`. The `Blueprint` mechanism is a Python interface that allows
you to do advanced initialisation of objects.

In particular, it enables partial application of arguments to a `Blueprint`. Since `chz` objects
are immutable, this can be a good substitute for a complex initialisation procedure that relies
on mutability.

```python
blueprint = chz.Blueprint(Experiment)
# Note that apply modifies the blueprint in place, use blueprint.clone() to make a copy
blueprint.apply({"encoding_name": "gpt2", "...n_layers": 100})
blueprint.apply({"model": Transformer})
blueprint.apply({"model.n_layers": 10_000})
blueprint.apply({"model.n_layers": Castable("10_000")})

experiment = blueprint.make()
# experiment = Experiment(model=Transformer(n_layers=10_000), encoding_name="gpt2")
```

Partial application is lazy and non-destructive. In particular, if you do something incorrect, you
will only get errors when you actually try to instantiate, via `make`.

If for some reason you need the type aware casting logic that `chz` you get via the command line,
you can opt in to it when using `Blueprint.apply` by wrapping your value in `Castable`, e.g.
`blueprint.apply({"n_layers": Castable("100")})`.

Note that if you already have a `chz` object and you want to replace a field on it, you can use
`chz.replace`; this works similarly to `dataclasses.replace`.

## Blueprint polymorphism recap

Roughly, the core idea of polymorphic construction is that instead of only being able to assign
values to fields, you can also assign the return values of a call to fields:

If `chz` sees `field=value`, this is similar to `X(field=value)`. But if `chz` sees
`field=value field.a=1 field.b=2`, this is similar to `X(field=value(a=1, b=2))`.

For a full explanation of the Blueprint algorithm, see [05_blueprint.md#blueprint-algorithm].

### Discovery and interpretation of valid polymorphic values

When figuring out which class you mean to instantiate when you do `model=Transformer`, `chz` will
look at all currently created subclasses of `Model` to find the right one. When calling functions,
`chz` will look at all the functions in the module of the relevant config.

You can also specify a fully qualified path like `module:ClassName` / `package.module:function`
and `chz` will import and find your object. This can let you avoid ambiguity or reliance on
import time side effects.

This discovery process can also be customised via `meta_factory`. This is an advanced feature,
see `chz/factories.py` for more details.

TODO: talk about some of the more advanced tricks here (i.e. look at some of the things from
`test_factories.py`)

## `blueprint_unspecified`

This is easiest to understand by example.

```python
@chz.chz
class Model: ...

@chz.chz
class Transformer(Model): ...

@chz.chz
class Experiment:
    model: Model = chz.field(blueprint_unspecified=Transformer)
```

Say you have an entrypoint that can run an experiment on an arbitrary model.

But in practice, you mostly want to run experiments on `Transformer`s. Rather than force your users
to have to specify `model=Transformer` every time, you can use `blueprint_unspecified` to specify
what `chz` should attempt to polymorphically construct if there isn't an argument specified.

#### Confusion about `blueprint_unspecified` and `default/default_factory`

Users of `chz` are commonly confused by the relationship between `blueprint_unspecified` and
`default/default_factory`. There is no relationship! `Blueprint` will **never** look at the value
of `default/default_factory`. The primary interaction with `Blueprint`s is that their absence or
presence will mark an argument as required or not.

I recommend when in doubt not using `default/default_factory` for fields you wish to
polymorphically construct.

(One could ask why `chz` doesn't attempt to infer `blueprint_unspecified` from
`default/default_factory`. This is a good question, but has a longer answer than is worth going
into here)

## Presets or shared configuration

Partial application gives you the ability to add presets.
For example, consider a typical experiment command line:
```
               ⤹ preset name
python main.py small_gpt seed=217 name=just_a_lil_guy
               ~~~~~~~~~
```

You could mimic this with something like:

```python
@chz.chz
class Experiment: ...

presets: dict[str, chz.Blueprint] = {
    "small_gpt": chz.Blueprint(Experiment).apply(
        {"seed": 0, "model": Transformer, "model.n_layers": 4},
        layer_name="small gpt preset",
    ),
    ...
}

def main():
    preset, *argv = sys.argv[1:]
    blueprint = presets[preset].clone()
    experiment = blueprint.make_from_argv(argv)
```

The layer name is a subtle thing that's quite important, since adding `--help` to any command line
will show you exactly where each value being used is coming from:
```
Arguments:
  model                Model    Transformer (from small gpt preset)
  model.encoding_name  str      'gpt2' (default)
  model.n_layers       int      4 (from small gpt preset)
  ...
```

I will some day add built-in support for presets in `chz` in the future.
For now, add your own extensions to manipulate `Blueprint`s.

## Custom tooling

The `Blueprint` APIs are powerful. At OpenAI, there's a number of interesting custom tools
that build on top of the `Blueprint` APIs.

In particular, take a look at `Blueprint._make_lazy`. It's also worth familiarising yourself with
the `_ArgumentMap` class.

Don't be scared by the underscores. Just add tests for the extensions you write.

## Undocumented Blueprint features

There are a number of powerful `Blueprint` features that are not yet documented.
The good news is they all have tests that demonstrate their usage.

I mention this here because if you hit some case you would like to express, it's possible that
there is a way to express this.

## Blueprint algorithm

The source code is of course the best source of truth.

Very very roughly, the algorithm is:

1. Blueprint arguments are "layers" of dicts from arguments (possibly wildcard) to value provided.
2. For a given parameter `foo.bar`, find the latest layer that has an argument matching
   the `foo.bar` parameter.
3. If there is no matching argument, check to see if we can call something to construct the value.

    1. Check to see if there is a callable specified by `blueprint_unspecified`
    2. Otherwise, use `chz`'s best guess (if `chz` has one)
    3. Attempt to call this function, with recursive discovery of parameters.
    4. If this doesn't work out, we'll use `default/default_factory` if it exists, if not, we'll
       error for missing a required argument.

4. If there is such an argument, we now attempt to use it!
5. Check if it's a valid value for the parameter (or is a `Castable` that can be casted to the
   correct type). This is done by checking if the value is of the right type and if there are not
   additional subarguments specified.
6. Otherwise, attempt to use the value as a callable we can call to construct the value (or a
   `Castable` that can be casted to a callable).

### [Next section — Serialisation](./06_serialisation.md)
