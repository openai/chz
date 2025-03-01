## Declarative object model

In the beginning there was `attrs`... although people may be more familiar with its stripped down
nephew, `dataclasses`. `chz` continues in the same tradition.

This should feel familiar:

```python
@chz.chz
class Experiment:
    name: str
    steps: int
    checkpoint_dir: str = "az://oai/default"
```

A quick comparison to `dataclasses`:
- `chz` is not meant as a better `class`, but as a solution for configuration. It is opinionated
  and specialised in various ways that `dataclasses` is not.
- `chz` has exclusively keyword-only fields. This is generally saner and solves various problems
  with `dataclasses`, especially in situations involving inheritance.
- `chz` is immutable only. Configuration should not be mutable. `chz` supports partial
  application in ways that should hopefully obviate the need for mutable configuration
  (as we'll see later); you can also `chz.replace` to get a new object.
- `chz`'s implementation makes different tradeoffs

## Fields, and specifying defaults

`chz` lets you customise the fields of your objects using the `chz.field` function.

The following example shows different ways you can specify the default value for a field:

```python
@chz.chz
class Experiment:
    name: str
    steps: int

    # directly assign a default value, useful for simple, immutable types
    checkpoint_dir: str = "az://oai/default"
    # via the `default` argument to `chz.field`, useful if you need to customise your field
    # (like hiding it from the repr), but still have a default
    password: str = chz.field(default="hunter2", repr=False)
    # via the `default_factory` argument to `chz.field`, useful if the default is mutable or
    # expensive to compute
    dataset: list[str] = chz.field(default_factory=download_all_of_wikipedia, doc="A dataset!")
```

See [`chz.field` docs](./22_field_api.md) for more details.

## Immutability

`chz` objects are immutable. This is a deliberate and non-negotiable design choice:

```python
e = Experiment(name="train_job", steps=100)
e.checkpoint_dir = "az://this/wont/work"  # raises FrozenInstanceError
```

That said, there are a couple patterns that are useful. If you need to compute derived data from
existing fields, use `@chz.init_property` (or `@property` or `@functools.cached_property`):

```python
@chz.chz
class Experiment:
    name: str
    steps: int

    @chz.init_property
    def log_path(self) -> str:
        return re.sub(r"[^a-zA-Z]", "", self.name)
```

`chz.init_property` works exactly like `functools.cached_property`, except that it is automatically
accessed during initialisation. This surfaces errors more reliably. Think of this as a replacement
for `dataclasses.field(init=False)`.

For complex initialisation logic, `chz` has a
[`Blueprint` mechanism](04_command_line.md#blueprints-and-partial-application) that is really
powerful. This allows you to accomplish things like partial application, where you only specify some
of your attributes at a time, or type aware parsing.

Note that if you already have a `chz` object and you want to replace a field on it, you can use
`chz.replace`; this works similarly to `dataclasses.replace`.

## No `__post_init__`

Note that `chz` does **not** have a `__post_init__` equivalent.

If you wanted a `__post_init__` to do additional validation, `chz` has first-class support for
validation. See [validation](./03_validation.md) for details.

If you need arbitrary logic to determine a default value, consider using `default_factory`.

If you need to munge your field based on the value of other fields, consider using `@property` to
do something equivalent, or a `munger`.

See [details and examples](./21_post_init.md) for more guidance with this use case. The details
document also describes the "magix prefix" mechanism (`X_`) you may see in use with `chz`.

### [Next section — Validation](./03_validation.md)
