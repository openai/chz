import re

import chz


def test_root_polymorphism():
    @chz.chz
    class X:
        a: int
        b: str = "str"

    @chz.chz
    class Y(X):
        c: float = 1.0

    def foo(a: int, b: str = "default", c: float = 3.0):
        return Y(a=a, b=b, c=c)

    assert chz.Blueprint(X).apply({"a": 0}).make() == X(a=0, b="str")
    assert chz.Blueprint(X | None).apply({"a": 0}).make() == X(a=0, b="str")

    assert chz.Blueprint(X).apply({"": Y, "a": 0}).make() == Y(a=0, b="str", c=1.0)
    assert chz.Blueprint(X).apply({"": foo, "a": 2}).make() == Y(a=2, b="default", c=3.0)

    assert chz.Blueprint(object).apply({"": X, "a": 1}).make() == X(a=1, b="str")
    assert chz.Blueprint(object).apply({"": foo, "a": 1}).make() == Y(a=1, b="default", c=3.0)

    # TODO: make help better if root is object or Any and no arguments are provided
    assert re.fullmatch(
        r"""Entry point: object

  The base class of the class hierarchy.*

Arguments:
  <entrypoint>  object  test_blueprint_root_polymorphism:test_root_polymorphism.<locals>.X                The base class of the class hierarchy.*
  a             int     1
  b             str     'str' \(default\)
""",
        chz.Blueprint(object).apply({"": X, "a": 1}).get_help(),
        flags=re.DOTALL,
    )

    assert re.fullmatch(
        r"""Entry point: object

  The base class of the class hierarchy.*

Arguments:
  <entrypoint>  object  test_blueprint_root_polymorphism:test_root_polymorphism.<locals>.foo              The base class of the class hierarchy.*
  a             int     1
  b             str     'default' \(default\)
  c             float   3.0 \(default\)
""",
        chz.Blueprint(object).apply({"": foo, "a": 1}).get_help(),
        flags=re.DOTALL,
    )
