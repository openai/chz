import pytest

from chz.blueprint import Blueprint, Castable, beta_blueprint_to_argv
from chz.blueprint._argmap import ArgumentMap, Layer, join_arg_path
from chz.blueprint._wildcard import _wildcard_key_match, wildcard_key_to_regex


def test_wildcard_key_to_regex():
    assert wildcard_key_to_regex("a.b.c").pattern == r"a\.b\.c"
    assert wildcard_key_to_regex("a...c").pattern == r"a\.(.*\.)?c"
    assert wildcard_key_to_regex("...a").pattern == r"(.*\.)?a"
    assert wildcard_key_to_regex("...a...c").pattern == r"(.*\.)?a\.(.*\.)?c"
    with pytest.raises(ValueError, match="Wildcard not allowed at end of key"):
        wildcard_key_to_regex("...")
    with pytest.raises(ValueError, match="Wildcard not allowed at end of key"):
        wildcard_key_to_regex("a...")


def test_wildcard_key_match():
    assert _wildcard_key_match("a.b.c", "a.b.c")
    assert _wildcard_key_match("a...c", "a.b.c")
    assert _wildcard_key_match("...c", "a.b.c")
    assert _wildcard_key_match("...a...c", "a.b.c")
    assert _wildcard_key_match("...a.b.c", "a.b.c")
    assert _wildcard_key_match("...a.b...c", "a.b.c")
    assert _wildcard_key_match("...a...b.b...a", "a.b.x.b.b.a")
    assert _wildcard_key_match("...x.y.z", "x.y.z")
    assert not _wildcard_key_match("a.b.d", "a.b.c")
    assert not _wildcard_key_match("...a", "a.b.c")
    assert not _wildcard_key_match("a...b", "a.b.c")
    assert not _wildcard_key_match("...a", "xxa")
    assert not _wildcard_key_match("...a...b.b...a", "a.b.x.b.c.a")
    assert not _wildcard_key_match("...a...y", "a...a...z")
    assert not _wildcard_key_match("...a...b...a", "a...b...a...b...b...a.z")

    assert wildcard_key_to_regex("a.b.c").fullmatch("a.b.c")
    assert wildcard_key_to_regex("a...c").fullmatch("a.b.c")
    assert wildcard_key_to_regex("...c").fullmatch("a.b.c")
    assert wildcard_key_to_regex("...a...c").fullmatch("a.b.c")
    assert wildcard_key_to_regex("...a.b.c").fullmatch("a.b.c")
    assert wildcard_key_to_regex("...a.b...c").fullmatch("a.b.c")
    assert wildcard_key_to_regex("...a...b.b...a").fullmatch("a.b.x.b.b.a")
    assert wildcard_key_to_regex("...x.y.z").fullmatch("x.y.z")
    assert not wildcard_key_to_regex("a.b.d").fullmatch("a.b.c")
    assert not wildcard_key_to_regex("...a").fullmatch("a.b.c")
    assert not wildcard_key_to_regex("a...b").fullmatch("a.b.c")
    assert not wildcard_key_to_regex("...a").fullmatch("xxa")
    assert not wildcard_key_to_regex("...a...b.b...a").fullmatch("a.b.x.b.c.a")
    assert not wildcard_key_to_regex("...a...y").fullmatch("a...a...z")
    assert not wildcard_key_to_regex("...a...b...a").fullmatch("a...b...a...b...b...a.z")


def test_join_arg_path():
    assert join_arg_path("parent", "child") == "parent.child"
    assert join_arg_path("grand.parent", "child") == "grand.parent.child"
    assert join_arg_path("parent", "...child") == "parent...child"
    assert join_arg_path("grand...parent", "child") == "grand...parent.child"
    assert join_arg_path("", "child") == "child"
    assert join_arg_path("", "...child") == "...child"


def test_arg_map():
    layer = Layer({"a.b.c": 0, "a.b.c.one": 1, "a.b.c.two": 2}, None)
    arg_map = ArgumentMap([layer])

    assert arg_map.get_kv("a.b.c.one").key == "a.b.c.one"
    assert arg_map.get_kv("a.b.c.two").key == "a.b.c.two"
    assert arg_map.get_kv("a.b") == None
    assert arg_map.get_kv("a.b.c.zero") == None
    assert arg_map.get_kv("a.b.d") == None

    assert arg_map.subpaths("a.b.c") == ["", "one", "two"]
    assert arg_map.subpaths("a.b.c", strict=True) == ["one", "two"]
    assert arg_map.subpaths("a.b.c.one") == [""]
    assert arg_map.subpaths("a.b.c.one", strict=True) == []

    layer = Layer({"prefix_suffix": 1}, None)
    arg_map = ArgumentMap([layer])

    assert arg_map.subpaths("prefix") == []
    assert arg_map.subpaths("prefix", strict=True) == []

    layer = Layer({"": 1, "a": 2}, None)
    arg_map = ArgumentMap([layer])

    assert arg_map.subpaths("") == ["", "a"]
    assert arg_map.subpaths("", strict=True) == ["a"]

    layer_wildcard = Layer({"a...c.one": 1, "a...c.two": 2}, None)
    arg_map = ArgumentMap([layer_wildcard])

    assert arg_map.get_kv("a.b.c.one").key == "a...c.one"
    assert arg_map.get_kv("a.b.b.b.b.c.one").key == "a...c.one"

    assert arg_map.subpaths("a.b.c") == ["one", "two"]
    assert arg_map.subpaths("a.b.c.one") == [""]
    assert arg_map.subpaths("a.b.c.one", strict=True) == []

    layer_wildcard = Layer({"...one": 1}, None)
    arg_map = ArgumentMap([layer_wildcard])

    assert arg_map.subpaths("a.b.c.one") == [""]
    assert arg_map.subpaths("a.b.c.two") == []
    assert arg_map.subpaths("a.b.c.one", strict=True) == []

    layer_wildcard = Layer({"a...one...b...one": 1}, None)
    arg_map = ArgumentMap([layer_wildcard])

    assert arg_map.subpaths("a.one.x.one") == []

    layer_wildcard = Layer({"...prefix_suffix": 1}, None)
    arg_map = ArgumentMap([layer_wildcard])

    assert arg_map.subpaths("something.prefix") == []
    assert arg_map.subpaths("something.prefix", strict=True) == []


def test_layer():
    l = Layer({"...a": 0, "a": 1}, None)
    assert l.get_kv("a") == ("a", 1)
    l = Layer({"a": 1, "...a": 0}, None)
    assert l.get_kv("a") == ("a", 1)

    l = Layer({"...z": 1, "...x...y...z": 2, "...y...z": 3}, None)
    assert l.get_kv("x.y.z") == ("...x...y...z", 2)


def test_collapse_layers():
    class Dummy:
        pass

    from chz.blueprint._argv import _collapse_layers

    b = Blueprint(Dummy)
    b.apply({"a.b.c.d": 3, "a...d": 4, "...d": 5, "a...e": 7, "...e": 6, "a.b.c.d.f": 9})
    b.apply({"...f": 10})
    assert set(_collapse_layers(b)) == {
        ("a.b.c.d", 3),
        ("a...d", 4),
        ("...d", 5),
        ("a...e", 7),
        ("...e", 6),
        ("...f", 10),
    }

    b = Blueprint(Dummy)
    b.apply({"a.b.c.d": 3})
    b.apply({"a...d": 4})
    b.apply({"...d": 5})
    b.apply({"a...e": 7})
    b.apply({"...e": 6})
    b.apply({"a.b.c.d.f": 9})
    b.apply({"...f": 10})
    assert set(_collapse_layers(b)) == {("...d", 5), ("...e", 6), ("...f", 10)}

    b = Blueprint(Dummy)
    b.apply({"...d": 5})
    b.apply({"a.b.c.d": 3})
    b.apply({"a...d": 4})
    b.apply({"...f": 10})
    b.apply({"a.b.c.d.f": 9})
    assert set(_collapse_layers(b)) == {("...d", 5), ("a...d", 4), ("...f", 10), ("a.b.c.d.f", 9)}

    b = Blueprint(Dummy)
    b.apply({"...d": 5, "a.b.c.d": 3, "a...d": 4, "...f": 10, "a.b.c.d.f": 9})
    assert set(_collapse_layers(b)) == {
        ("...d", 5),
        ("a.b.c.d", 3),
        ("a...d", 4),
        ("...f", 10),
        ("a.b.c.d.f", 9),
    }


def test_collapse_blueprint_to_argv():
    class Dummy:
        pass

    b = Blueprint(Dummy)
    b.apply({"...d": 5})
    b.apply({"a.b.c.d": 3})
    b.apply({"a...d": 4})
    b.apply({"...f": 10})
    b.apply({"a.b.c.d.f": 9})
    b.apply({"a.b.c.d.f.e": None})
    assert beta_blueprint_to_argv(b) == [
        "...d=5",
        "a...d=4",
        "...f=10",
        "a.b.c.d.f=9",
        "a.b.c.d.f.e=None",
    ]


def test_apply_from_argv():
    class Dummy:
        pass

    from chz.blueprint._argv import _collapse_layers

    b = Blueprint(Dummy)
    b.apply_from_argv(["...d=5"])

    assert beta_blueprint_to_argv(b) == ["...d=5"]
    assert _collapse_layers(b)[0][1].value == "5"


def test_apply_with_types():
    class Dummy:
        pass

    b = Blueprint(Dummy)
    b.apply({"a": 1, "b": beta_blueprint_to_argv, "c": Blueprint})
    assert beta_blueprint_to_argv(b) == [
        "a=1",
        "b=chz.blueprint._argv:beta_blueprint_to_argv",
        "c=chz.blueprint._blueprint:Blueprint",
    ]


def test_castable_eq():
    assert Castable("None") == Castable("None")
    assert Castable("None") == None

    assert Castable("1") == Castable("1")
    assert Castable("1") == 1

    assert Castable("1") != 2
    assert Castable("x") != 2
