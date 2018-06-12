from marshmallow.fields import Integer, Nested, Str

from teal.query import Between, Equal, ILike, Or, Query
from teal.teal import Teal
from teal.utils import compiled


def test_query(app: Teal):
    with app.app_context():
        Device = app.resources['Device'].MODEL

        class Q(Query):
            idq = Or(Equal(Device.id, Str()))
            modelq = ILike(Device.model)

        schema = Q()
        query = schema.load({'idq': ['a', 'b', 'c'], 'modelq': 'foobar'})
        s, params = compiled(Device, query)
        # Order between query clauses can change
        assert 'device.model ILIKE %(model_1)s' in s
        assert '(device.id = %(id_1)s OR device.id = %(id_2)s OR device.id = %(id_3)s' in s
        assert params == {'id_2': 'b', 'id_3': 'c', 'id_1': 'a', 'model_1': 'foobar%'}


def test_query_nested(app: Teal):
    """Checks that nested queries work."""
    with app.app_context():
        Device = app.resources['Device'].MODEL

        class Inner(Query):
            foo = ILike(Device.model)

        class Q(Query):
            idq = Between(Device.id, Integer())
            componentq = Nested(Inner)

        schema = Q()
        query = schema.load({'idq': [1, 4], 'componentq': {'foo': 'bar'}})
        s, params = compiled(Device, query)
        assert 'device.id BETWEEN %(id_1)s AND %(id_2)s AND device.model ILIKE %(model_1)s' in s
        assert params == {'id_1': 1, 'model_1': 'bar%', 'id_2': 4}
