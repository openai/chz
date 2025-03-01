## Quick start

Turn any function into a command line tool:

```python
import chz

def main(name: str, age: int) -> None:
    print(f"Hello, {name}! You are {age} years old.")

if __name__ == "__main__":
    chz.entrypoint(main)

# python script.py name=foo age=21
```

Or instantiate a class containing your configuration:

```python
import chz

@chz.chz
class PersonConfig:
    name: str
    age: int

def main(c: PersonConfig) -> None:
    print(f"Hello, {c.name}! You are {c.age} years old.")

if __name__ == "__main__":
    chz.nested_entrypoint(main)

# python script.py name=foo age=21
```

### [Next section — Object Model](./02_object_model.md)
