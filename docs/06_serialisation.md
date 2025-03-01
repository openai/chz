## Serialisation and deserialisation

`chz` will one day have a great story for versioned serialisation and deserialisation.

The main obstacle is that I'm busy and cowardly. Note also that it's easy to roll your own
*un*versioned serialisation and deserialisation.

There are two utility functions in `chz` that you may find useful:
`chz.beta_to_blueprint_values` and `chz.asdict`.

Example:
```python
import chz

@chz.chz
class P:
    x: float
    y: float

@chz.chz
class C:
    s: str
    p: P

obj = C(s="foo", p=P(x=1.0, y=2.0))

print(chz.beta_to_blueprint_values(obj))
# {'s': 'foo', 'p': <class '__main__.P'>, 'p.x': 1.0, 'p.y': 2.0}
print(chz.Blueprint(type(obj)).apply(chz.beta_to_blueprint_values(obj)).make())
# C(s='foo', p=P(x=1.0, y=2.0))

print(chz.asdict(obj))
# {'s': 'foo', 'p': {'x': 1.0, 'y': 2.0}}
```

<details>
<summary>Thoughts on pickle</summary>

Pickle is actually totally fine here, if you don't need human readability.

`chz` is powerful enough that the ability to execute arbitrary code when deserialising is mostly
going to be the same as `pickle`'s.

The other thing `pickle` doesn't give you is versioning. Here's a dumb hack that allows evolution
for basic field additions.

```python
import pickle
import chz
from chz.util import MISSING

@chz.chz
class A:
    a: int

d = pickle.dumps(A(a=5))

@chz.chz
class A:
    a: int
    b: bool = True

    def __setstate__(self, state):
        for field in self.__chz_fields__.values():
            if field.x_name not in state:
                if field._default is not MISSING:
                    state[field.x_name] = field._default
                if field._default_factory is not MISSING:
                    state[field.x_name] = field._default_factory()
        self.__dict__.update(state)
        return self

print(pickle.loads(d))
```
</details>

### [Next section — Post Init](./21_post_init.md)
