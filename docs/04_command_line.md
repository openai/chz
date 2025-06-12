## Command line parsing

Type aware CLIs are really great.
These let you focus on writing code, with types, and you get a CLI for free.

`chz` gives this to you as well:

```python
def launch_run(name: str, steps: int, checkpoint_dir: str = "az://oai/default"):
    ...

if __name__ == "__main__":
    chz.entrypoint(launch_run)

# The command line:
# name=foo steps=100
# becomes:
# launch_run(name="foo", steps=100)
```

`chz` will also let you parse into an object:

```python
@chz.chz
class Experiment:
    name: str
    steps: int
    checkpoint_dir: str = "az://oai/default"


def main():
    experiment = chz.entrypoint(Experiment)
    ...

if __name__ == "__main__":
    main()

# The command line:
# name=foo steps=100 checkpoint_dir=az://oai/somewhere
# becomes:
# experiment = Experiment(name="foo", steps=100, checkpoint_dir="az://oai/somewhere")
```

If you have a `main` function that takes a single argument that's a `chz` object, you can have it
serve as an entrypoint by using `chz.nested_entrypoint`:

```python
def main(experiment: Experiment):
    ...

if __name__ == "__main__":
    chz.nested_entrypoint(main)
```

All of this is pretty straightforward. Here's a case `chz` handles that's a bit more interesting:
handling parsing when some of your fields are nested `chz` objects.

```python
@chz.chz
class Model:
    encoding: str

@chz.chz
class Experiment:
    name: str
    steps: int
    model: Model

# name=foo steps=100 model.encoding=gpt2
# becomes
# Experiment(name="foo", steps=100, model=Model(encoding="gpt2"))
```

## Hyphens

If you like `--hyphens` for your command line arguments, just use
`chz.entrypoint(..., allow_hyphens=True)` or similar.

But the zero hyphen life is pretty great once you get used to it.

## Polymorphic construction

Here's something only `chz` lets you do... what if you want `Model` to be polymorphic? That is,
maybe you want to be able to specify `model=Transformer` or `model=Diffusion`.

Or maybe you want to construct a field by calling some arbitrary factory function.

```python
import chz

def wikipedia_text(seed: int) -> Dataset:
    """Function that produces a dataset."""

@chz.chz
class Model:
    encoding_name: str = "gpt2"

@chz.chz
class Transformer(Model):
    n_layers: int = 1000
    d_model: int = 100000

@chz.chz
class Experiment:
    model: Model
    dataset: Dataset

experiment = chz.entrypoint(Experiment)

# The command line:
# model=Transformer model.n_layers=10 dataset=wikipedia_text dataset.seed=217
# becomes:
# Experiment(model=Transformer(n_layers=10), dataset=wikipedia_text(seed=217))
```

This is really powerful. Recursive polymorphic construction allows you to separate concerns more
clearly and helps reduce boilerplate.

If you're familiar with the "callable" pattern we sometimes end up with in our frameworks (e.g.
"dataset_callable") -- this enables having an interface that isn't a complete kludge. This
encourages modularity and allows for easy dependency injection. It is common for other libraries
in this space, to end up infecting all of your code; polymorphic construction helps
you avoid this.

In other other words, many tools will let you construct an `X` by specifying `...` to feed to
`X(...)`. But chz lets you construct an `X` by specifying both callee and arguments in `...(...)`

Anyway, hopefully this all adds up to fewer 1000 line launch scripts or registries or horrible
interfaces for parametrising datasets when using `chz`.

This is probably the primary interesting feature in `chz`.

## Wildcards

It can be a little tiresome specifying fully qualified paths for every field you want to set.
To aid with this, `chz` supports wildcards in your blueprint arguments using "...". For example:
```
model=Transform ...encoding=gpt2 model...activation_fn=gelu
```
This will set `encoding` on all nested objects that take an `encoding` argument, and set
`activation_fn` on all nested objects inside of `model` that take an `activation_fn` argument.
Note that wildcards can match multiple (potentially nested) fields.

Wildcard use is somewhat discouraged, particularly so outside of a command line context.

## Discoverability, `--help`, and errors

Programs that use `chz.entrypoint` also get you a reasonable `--help` out of the box.
```
$ python script.py --help
WARNING: Missing required arguments for parameter(s): dataset

Entry point: Experiment

Arguments:
  model                Model    Model (meta_factory)
  model.encoding_name  str      'gpt2' (default)
  dataset              Dataset  -
```

One important note about `--help`: polymorphic construction means that arguments you specify can
change the set of arguments you need to specify. For instance, in the above example,
`model=Transformer` will allow you to also specify `model.n_layers` and `model.d_model`.

However, passing `--help` to a `chz` script along with arguments, will show you all the arguments
you can specify given the arguments you've already specified. That is, passing
`model=Transformer --help` will show `model.n_layers` and `model.d_model` in the output.
```
$ python script.py model=Transformer --help
WARNING: Missing required arguments for parameter(s): dataset

Entry point: Experiment

Arguments:
  model                Model    Transformer (from command line)
  model.encoding_name  str      'gpt2' (default)
  model.n_layers       int      1000 (default)
  model.d_model        int      100000 (default)
  dataset              Dataset  -
```

Note that `--help` will also show you the mapping of arguments you specify to fields:
```
$ python script.py model=Transformer ...n_layers=10 model.encoding_name=cl100k_base --help
WARNING: Missing required arguments for parameter(s): dataset

Entry point: Experiment

Arguments:
  model                Model    Transformer (from command line)
  model.encoding_name  str      cl100k_base (from command line)
  model.n_layers       int      10 (from command line)
  model.d_model        int      100000 (default)
  dataset              Dataset  -
```

If you misspell an argument, `chz` will tell you what you probably meant. This fuzzy detection logic
works well even for wildcard arguments.
```
chz.blueprint.ExtraneousBlueprintArg: Extraneous Blueprint argument 'modell' for __main__.Experiment
Did you mean 'model'?
```

Finally, while `chz` allows you to clobber arguments, it does not allow arguments to go completely
unused. This is important for sanity, but somehow a common bug in some CLI libraries, like `fire`.

## Variadic parameters

chz supports polymorphic construction through variadic parameters. This works for lists, tuples,
dicts (with str keys) and `TypedDict`s:

```python
@chz.chz
class Eval:
    name: str

@chz.chz
class Experiment:
    evals: list[Eval]

experiment = chz.entrypoint(Experiment)

# The command line:
# evals.0.name=foo evals.1.name=bar
# becomes:
# Experiment(evals=[Eval(name="foo"), Eval(name="bar")])
```

Variadic parameters can also be polymorphic, for instance, you could do:
```python
# evals.0=EvalSubclass evals.0.name=foo evals.1.name=bar
# becomes:
# Experiment(evals=[EvalSubclass(name="foo"), Eval(name="bar")])
```

## `Blueprint`s, briefly

We'll talk about `Blueprint`s more in the next section. For now, all you need to know is that the
`Blueprint` class is the API that powers `chz`'s command line functionality. The `chz.entrypoint`
function we saw above is basically doing:
```
def entrypoint(target: Callable[..., _T]) -> _T:
    return Blueprint(target).make_from_argv(sys.argv[1:])
```

## Casting

The arguments you provide on the command line are strings. However, `chz` wants to give you your
arguments with the correct type. By default, `chz` will try to cast your arguments for you to
the correct type.

This casting is a process you may wish to customise.

The first method is by attaching a `__chz_cast__` classmethod to the target type.
```python
@dataclass
class Duration:
    seconds: int

    @classmethod
    def __chz_cast__(cls, value: str):
        try:
            return Duration(int(value.strip("hms")) * {"h": 3600, "m": 60, "s": 1}[value[-1]])
        except Exception as e:
            raise CastError(f"Could not cast {value!r} to {cls.__name__}") from e

@chz.chz
class Args:
    t: Duration

assert chz.Blueprint(Args).apply({"t": Castable("1h")}).make() == Args(t=Duration(3600))
```
In the above, since `Duration` is used in the annotation, `chz` will attempt to use
`Duration.__chz_cast__` to cast `Castable("1h")` to the correct type.

The second method is by specifying a per-field function to `blueprint_cast` via `chz.field`:
```python
def cast_binary(value: str) -> int:
    try:
        return int(value, 2)
    except Exception as e:
        raise CastError(f"Could not cast {value!r} to binary") from e

@chz.chz
class Args:
    binary: int = chz.field(blueprint_cast=cast_binary)

assert chz.Blueprint(Args).apply({"binary": Castable("101")}).make() == Args(binary=5)
```

Field level casts will override the `__chz_cast__` method if both are applicable.

Casting only applies to `Blueprint` (not `__init__` of your `chz` class), and only if the value
passed to the `Blueprint` is a `Castable`. Python is a strongly typed language, this is a good
thing, `chz` will not change your types willy nilly.

### CLI from a class

`chz` lets you easily create a script entrypoint based on the methods on a class using
`chz.methods_entrypoint`.

For example, given main.py:
```python
import chz

@chz.chz
class Run:
    name: str

    def launch(self, cluster: str):
        "Launch a job on a cluster"
        return ("launch", self, cluster)

if __name__ == "__main__":
    print(chz.methods_entrypoint(Run))
```

Try out the following command line invocations:
```
python main.py launch self.name=job cluster=owl
python main.py launch --help
python main.py --help
```

Note that you can rename the `self` argument in your method to something else.

### Universal CLI

```python
import chz

chz.entrypoint(object)
```

This script probably isn't actually directly useful, but just to show you the power of `chz`, it
will let you call most functions or create most objects.
Try:
- `python -m chz.universal '=print' '0=hello' '1=lambda name: name + "!"' '1.name=world'`
- `python -m chz.universal '=calendar:Calendar' --help`
See e.g. `test_root_polymorphism` for how you might actually want to use this.

### [Next section — Blueprints](./05_blueprint.md)
