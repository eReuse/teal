from unittest.mock import MagicMock, call

from teal import utils
from teal.resource import Resource


def test_import_resource():
    """Tests that only subclasses of resource are imported."""

    class module:
        class Foo(Resource):
            pass

        class Bar(Resource):
            pass

        class ThisIsNotResource:
            pass

        RandomVar = 3
        Res = Resource

    x = set(utils.import_resource(module))
    assert x == {module.Foo, module.Bar}


def test_if_none_return_none():
    mocked = MagicMock()
    wrapped = utils.if_none_return_none(mocked)
    assert mocked.call_count == 0
    wrapped(None, 3)
    assert mocked.call_count == 1
    assert mocked.call_args == call(None, 3)
    wrapped(None, None)
    assert mocked.call_count == 1
