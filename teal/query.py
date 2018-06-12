from marshmallow import Schema as MarshmallowSchema
from marshmallow.fields import Field, List, Str, missing_
from sqlalchemy import Column, and_, between, or_


class ListQuery(List):
    """Base class for list-based queries."""

    def __init__(self, column: Column, cls_or_instance, **kwargs):
        self.column = column
        super().__init__(cls_or_instance, **kwargs)


class Between(ListQuery):
    """
    Generates a `Between` SQL statement.

    This method wants the user to provide exactly two parameters:
    min and max::

        f = Between(Model.foo, Integer())
        ...
        Query().loads({'f': [0, 100]}

    """

    def _deserialize(self, value, attr, data):
        l = super()._deserialize(value, attr, data)
        return between(self.column, *l)


class Equal(Field):
    """
    Generates an SQL equal ``==`` clause for a given column and value::

        class MyArgs(Query):
            f = Equal(MyModel.foo, Integer())
        MyArgs().load({'f': 24}) -> SQL: ``MyModel.foo == 24``

    """

    def __init__(self, column: Column, field: Field,
                 default=missing_, attribute=None, data_key=None, error=None, validate=None,
                 required=False, allow_none=None, load_only=False, dump_only=False,
                 missing=missing_, error_messages=None, **metadata):
        super().__init__(default, attribute, data_key, error, validate, required, allow_none,
                         load_only, dump_only, missing, error_messages, **metadata)
        self.column = column
        self.field = field

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column == self.field.deserialize(v)


class Or(List):
    """
    Generates an `OR` SQL statement. This is like a Marshmallow List field,
    so you can specify the type of value of the OR and validations.

    As an example, you can define with this a list of options::

        f = Or(Equal(Model.foo, Str(validates=OneOf(['option1', 'option2'])))

    Where the user can select one or more::

        {'f': ['option1']}

    And with ``Length`` you can enforce the user to only choose one option::

        f = Or(..., validates=Length(equal=1))
    """

    def _deserialize(self, value, attr, data):
        l = super()._deserialize(value, attr, data)
        return or_(v for v in l)


class ILike(Str):
    """
    Generates a insensitive `LIKE` statement for strings.
    """

    def __init__(self, column: Column,
                 default=missing_, attribute=None, data_key=None, error=None, validate=None,
                 required=False, allow_none=None, load_only=False, dump_only=False,
                 missing=missing_, error_messages=None, **metadata):
        super().__init__(default, attribute, data_key, error, validate, required, allow_none,
                         load_only, dump_only, missing, error_messages, **metadata)
        self.column = column

    def _deserialize(self, value, attr, data):
        v = super()._deserialize(value, attr, data)
        return self.column.ilike('{}%'.format(v))


class Query(MarshmallowSchema):
    """
    A Marshmallow schema that outputs SQLAlchemy queries when ``loading``
    dictionaries::

        class MyQuery(Query):
            foo = Like(Mymodel.foocolumn)

        Mymodel.query.filter(*MyQuery().load({'foo': 'bar'})).all()
        # Executes query SELECT ... WHERE foocolumn IS LIKE 'bar%'

    When used with ``webargs`` library you can pass generate queries
    directly from the browser: ``foo.com/foo/?where={'foo': 'bar'}``.
    """

    def load(self, data, many=None, partial=None):
        """
        Flatten ``Nested`` ``Query`` and add the list of results to
        a SQL ``AND``.
        """
        values = []
        for x in super().load(data, many, partial).values():
            if isinstance(x, list):
                for y in x:
                    values.append(y)
            else:
                values.append(x)
        return and_(*values)

    def dump(self, obj, many=None, update_fields=True):
        raise NotImplementedError('Why would you want to dump a query?')
