import pytest
from marshmallow import ValidationError

from teal.fields import Natural, RangedNumber
from teal.resource import Schema


def test_ranged_number_min():
    """Tests the ``RangedNumber`` field when setting ``min``."""
    with pytest.raises(AssertionError):
        # At least add a min or max
        RangedNumber()

    class Foo(Schema):
        bar = RangedNumber(min=0)

    foo = Foo()

    foo.load({'bar': 1})
    with pytest.raises(ValidationError):
        foo.load({'bar': -1})


def test_ranged_number_both():
    """
    Tests the ``RangedNumber`` field when setting ``min`` and ``max``.
    """

    class Foo(Schema):
        bar = RangedNumber(min=0, max=10)

    foo = Foo()
    foo.load({'bar': 2})
    with pytest.raises(ValidationError):
        foo.load({'bar': 11})
    with pytest.raises(ValidationError):
        foo.load({'bar': -1})


def test_ranged_number_max():
    """
    Tests the ``RangedNumber`` field when setting ``max``.
    """

    class Foo(Schema):
        bar = RangedNumber(max=10)

    foo = Foo()
    foo.load({'bar': 9})
    foo.load({'bar': -20})
    with pytest.raises(ValidationError):
        foo.load({'bar': 11})


def test_natural():
    """Tests the ``Natural`` field."""

    class Foo(Schema):
        bar = Natural()

    foo = Foo()
    foo.load({'bar': 1})
    foo.load({'bar': 0})
    with pytest.raises(ValidationError):
        foo.load({'bar': -1})
    with pytest.raises(ValidationError, message={'bar': ['Not a valid Natural number.']}):
        foo.load({'bar': 1.1})
    with pytest.raises(ValidationError):
        foo.load({'bar': 1.0})
