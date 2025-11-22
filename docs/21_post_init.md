## No `__post_init__`; details and examples

There are a couple reasons why `chz` does not have a `__post_init__` equivalent for munging
your fields:
- `__post_init__` has bad ergonomics with immutable objects (e.g. you need to use
  `object.__setattr__` or some wrapper to mutate fields)
- `__post_init__` encourages non-local initialisation behaviour that can be hard to reason about
- `__post_init__`'s interaction with `super` is easy to mess up
- `__post_init__`'s interaction with static type checkers is bad (if you use munging in
  `__post_init__` to narrow types)

### Caveat!!

If I were to rewrite `chz` from scratch, I would do things a little bit differently here (and I
may yet change some of this stuff). In a tale as old as time, I ended up where we are today via a
several changes in response to several things over a period of several years. I have one more big
change planned at some point.

Most notably, chz sort of predates PEP 681. E.g. the `X_` stuff that is most incompatible with
PEP 681 was made inconvenient (it used to be `隐_`), but these things proved useful and I relented.

### No `__post_init__`

Here is some detail about the constraints posed by wanting static type checking to work.
Take a look at the following example:

```python
# This will error since chz does not have a __post_init__
@chz.chz
class Experiment:
    name: str
    steps: int
    wandb_log_name: Optional[str] = None

    def __post_init__(self):
        if self.wandb_log_name is None:
            self.wandb_log_name = self.name
        raise NotImplementedError("chz does not actually have a __post_init__; this is a hypothetical")
```

Now, anytime you try to use `experiment.wandb_log_name` you'll have to assert that it is not None
because the type checker doesn't know that `__post_init__` will always set it. This is a sorry
state of affairs.

### Solution that fully works with static type checkers

Compare that to doing:

```python
# Recommended solution
@chz.chz
class Experiment:
    name: str
    steps: int
    wandb_log_name: Optional[str] = None

    @chz.init_property
    def wandb_log_name_value(self) -> str:
        return self.wandb_log_name or self.name
```

Now use the `experiment.wandb_log_name_value` attribute instead. And if you mess it up and use the
wrong one, the type checker will warn you, since the types are different!

It does suck that you have to come up with a different name like `wandb_log_name_value`.
If you do this, I recommend using the `_value` suffix for this.

### Alternative "magic prefix" solution (does not fully work with static type checkers)

```python
# Alternative "magic prefix" solution
@chz.chz
class Experiment:
    name: str
    steps: int
    # chz will magically strip the "X_" in the __init__ parameter, and do the equivalent of
    # `self.X_wandb_log_name = wandb_log_name` in __init__.
    X_wandb_log_name: Optional[str] = None

    @chz.init_property
    def wandb_log_name(self) -> str:
        return self.X_wandb_log_name or self.name


# Now you can instantiate your object using `wandb_log_name` as a parameter
# ...but static type checkers will complain about all direct instantiations of your object
experiment = Experiment(name="train_job", steps=100, wandb_log_name=None)
assert experiment.wandb_log_name == "train_job"
```

One note for why this design: because definitions with the same name in classes clobber each other,
the field name needs to be different from the `init_property` name. Otherwise, `chz` is not able
to access the `chz.field` spec / default value for the field.

### Alternative "munging" solution (mostly works with static type checkers)


```python
# Alternative "munging" solution
@chz.chz
class Experiment:
    name: str
    steps: int
    # The value passed to the constructor will end up processed by the munger function
    # wandb_log_name: str = chz.field(munger=lambda self, value: value or self.name)

    # You can use the combinators in chz.mungers too, for example:
    # wandb_log_name: Optional[str] = chz.field(munger=attr_if_none("name"))

    # If the value passed to `__init__` can be of another type (say None), you can use x_type so
    # that type aware parsing continues to work
    wandb_log_name: str = chz.field(munger=attr_if_none("name"), x_type=str | None)


experiment = Experiment(name="train_job", steps=100, wandb_log_name=None)
```

As you can see, mungers can access any other attribute (which itself may be munged).
chz will handle the ordering well.

If you do something recursive, you will get an error. The way to handle this is to explicitly
access the raw unmunged value, which you can find on `self` with the `X_` prefix.

Currently munged values are validated both before and after munging. This allows you to rely on
validation during munging and as an invariant. The exact logic here may change in the future.

Note that munging is best for defaulting logic. If you wish to simply change command line parsing
logic, consider using `blueprint_cast` and `__chz_cast__` instead.

### Mechanics and `X_` prefix

Here's what chz is basically doing under the hood. When it sees:

```python
@chz.chz
class Args:
    foo: int = chz.field(default=1)
```
It will convert this to:
```python
@chz.chz
class Args:
    def __init__(self, foo: int = 1):
        self.X_foo = foo
        ...  # some other stuff, like validation

    @chz.init_property
    def foo(self) -> int:
        return self.X_foo
```
If there's a munger for the field `foo`, then the `init_property` added will do whatever the
munger does, instead of just returning `self.X_foo`.

This design has several advantages:
- This handles any graph of field reference between munging in attributes well without e.g. forcing
  ordering constraints on definitions
- We preserve a lot of information about intent
- We don't have to worry about non-idempotent munging, e.g. when doing `chz.replace`
- In fact, we can even detect impure or non-idempotent `init_property`
- Similarly, when deserialising, we could detect if `init_property` behaviour has changed
- It keeps semantics relatively consistent between all options discussed on this page
- It works well when you inherit from another chz class, but wish to override the field with an
  `init_property`


### [Next section — Field API](./22_field_api.md)
