## Validation

`chz` supports validation in a manner similar to `attrs`, but slightly nicer for class-level
validation. `chz` supports both field-level validation and class-level validation.

```python
from chz.validators import typecheck, gt

@chz.chz
class Fraction:
    # specify a validator for a given field
    numerator: int = chz.field(validator=typecheck)
    # or even multiple validators for a field!
    denominator: int = chz.field(validator=[typecheck, gt(0)])

    # class-level validator that can check multiple fields
    @chz.validate
    def _check_reduced(self):
        if math.gcd(self.numerator, self.denominator) > 1:
            raise ValueError("Fraction is not reduced")

Fraction(numerator="asdf", denominator=4)  # raises TypeError: Expected numerator to be int, got str
Fraction(numerator=2, denominator=0)  # raises ValueError: Expected denominator to be greater than 0, got 0
Fraction(numerator=2, denominator=4)  # raises ValueError: Fraction is not reduced
Fraction(numerator=1, denominator=2)  # works great!
```

Validation happens as part of the generated `__init__`.

All `@chz.init_property` defined on your class will also be accessed at `__init__` time, ensuring
that any errors raised when computing those properties are surfaced early.

## Type checking

`chz` is usable alongside static type checking. It also contains some facilities to do runtime
type checking.

`chz` does not currently default to doing runtime type checking. The upsides are limited, since:
- `chz` has powerful, type-aware command line parsing
- `chz` can be understood by static type checkers

However, runtime type checking has several downsides: it's slow, it's not actually sound, so cannot
be a substitute for a static type checker, it impedes certain kinds of interesting metaprogramming.
It's less clear how one would opt-out of runtime type checking than it is to opt-in (just add
a validator).

`chz` does not do implicit casting, like `pydantic`. I find this to be a huge footgun.
Python is a strongly typed language and this is for the better. `chz` does allow for some forms
of explicitly opted-in casting, as part of [the `Blueprint` mechanism](04_command_line.md#blueprints-and-partial-application).

With all that said, it remains easy to add runtime type checking! We saw an example of this on a
per-field basis above, but here's how to easily do this for all fields in a class:

```python
@chz.chz(typecheck=True)
class TypeCheckedAlphabet:
    alpha: int
    beta: str
    gamma: bytes

# This is approximately equivalent to adding the following validator:
#     @chz.validate
#     def typecheck_all_fields(self):
#         from chz.validators import for_all_fields, typecheck
#         for_all_fields(typecheck)(self)
```

`chz`'s runtime type checking is also quite advanced and better in several respects than other
open source libraries.

## Validation and inheritance

`chz`'s validation works as expected in the presence of inheritance: both class-level and
field-level validators are inherited by the child class.

There is one caveat: if you clobber a field in a child class, you will also clobber any field-level
validator specified in a parent class for that field, unless you explicitly respecify it.

`chz` currently does not allow overriding validators in subclasses. This is because it would
represent a Liskov substitution principle violation (and use cases are niche). If you need
this, have your validator call some other method which you can then freely override.

`chz` has some built-in validation, for instance, ensuring that fields do not clobber methods or
properties defined on the parent class, etc.

### [Next section — Command line](./04_command_line.md)
