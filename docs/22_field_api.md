## `chz.field`

`chz.field` takes the following parameters:

#### `default`

Like with `dataclasses`, the default value for the field (if any).

#### `default_factory`

Like with `dataclasses`, a function that returns the default value for the field.
Useful for mutable types, for instance, `default_factory=list`.

Note: this does not interact with parametrisation / `Blueprint` / `blueprint_unspecified` / `meta_factory`.
The only thing that matters to parametrisation is presence or absence of a
`default` or `default_factory`.

Perhaps a better name would be `lazy_default` (but unfortunately, this is not supported by PEP 681,
so static type checkers would lose the ability to understand the class).

#### `validator`

A function or list of functions that validate the field.
Field validators take two arguments: the instance of the class and the name of the field.

See also: [Validation](./03_validation.md)

#### `repr`

If a boolean, whether or not to include the field in the `__repr__` of the class.
If a callable, will be used to construct the `repr` of the field.

#### `doc`

The docstring for the field. Used in `--help`.

#### `metadata`

Arbitrary user-defined metadata to attach to the field. Useful when extending `chz`.

#### `munger`

Lets you adjust the value of a field. Essentially works the same as an init_property.

See also: [Alternative "munging" solution](./21_post_init.md)

#### `x_type`

Useful in combination with mungers. This specifies the type before munging that
will be used for parsing and type checking.

#### `meta_factory`

A metafactory represents the set of possible callables that can give us a value of a given type.

Describes the set of callables that are capable of returning a valid value for the field if given a
non-zero number of arguments.

For instance, the meta factory `chz.factories.subclass(Model)` is a description of the set of
callables that are capable of producing a `Model` (e.g. `{Transformer, Diffusion}`).

This was more useful in previous versions of `chz`, but now `chz` infers what you want to do
more reliably.

See also: the docs in `chz/factories.py`

#### `blueprint_unspecified`

This is the default callable `Blueprint` may attempt to call to get a value of the expected type.

See [Blueprint](./05_blueprint.md#blueprint_unspecified)

#### `blueprint_cast`

A function that takes a str and returns an object. On failure to cast,
it should raise `CastError`. Used to achieve custom parsing behaviour from the command
line. Takes priority over the `__chz_cast__` dunder method (if present on the
target type).

See also: [Casting](./04_command_line.md#casting)

### [Next section — Philosophy](./91_philosophy.md)
