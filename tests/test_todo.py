import pytest

import chz

# TODO: test inheritance, setattr, repr


def test_version():
    @chz.chz(version="b4d37d6e")
    class X1:
        a: int

    @chz.chz(version="b4d37d6e-3")
    class X2:
        a: int

    with pytest.raises(ValueError, match="Version 'b4d37d6e' does not match '3902ee27'"):

        @chz.chz(version="b4d37d6e")
        class X3:
            a: int
            b: int
