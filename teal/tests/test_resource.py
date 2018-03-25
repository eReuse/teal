from flask_sqlalchemy import SQLAlchemy

from teal.auth import Auth
from teal.db import POLYMORPHIC_ID, POLYMORPHIC_ON
from teal.resource import ResourceDefinition, Schema, View


def test_schema_type():
    class Foo(Schema): pass

    foo = Foo()
    assert foo.type == 'Foo'

    class FooSchema(Schema): pass

    foo_schema = FooSchema()
    assert foo_schema.type == 'Foo'


def test_model_type(db: SQLAlchemy):
    TYPE = 'Foo'

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        type = db.Column(db.String(50))

        __mapper_args__ = {
            POLYMORPHIC_ID: TYPE,
            POLYMORPHIC_ON: type
        }

    foo = Foo()
    assert foo.type == TYPE


def test_resource_def_init(db: SQLAlchemy):
    class FooSchema(Schema): pass

    class FooView(View): pass

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class FooDef(ResourceDefinition):
        SCHEMA = FooSchema
        RESOURCE_VIEW = FooView
        MODEL = Foo

    foo_def = FooDef(Auth())
    assert foo_def.schema.type == foo_def.type == 'Foo'
    assert foo_def.url_prefix == '/foos'
    assert foo_def.name == 'Foo'
