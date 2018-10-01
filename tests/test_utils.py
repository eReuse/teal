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
