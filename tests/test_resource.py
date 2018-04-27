import json
from copy import deepcopy

import pytest
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from marshmallow.fields import Integer

from teal.auth import Auth
from teal.config import Config
from teal.db import POLYMORPHIC_ID, POLYMORPHIC_ON
from teal.resource import Resource, Schema, View
from teal.teal import Teal


def test_schema_type():
    class Foo(Schema): pass

    foo = Foo()
    assert foo.t == 'Foo'

    class FooSchema(Schema): pass

    foo_schema = FooSchema()
    assert foo_schema.t == 'Foo'


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

    class FooDef(Resource):
        SCHEMA = FooSchema
        VIEW = FooView
        MODEL = Foo

    class MockApp:

        def __init__(self) -> None:
            self.auth = Auth()

    foos = FooDef(MockApp())
    assert foos.schema.t == foos.type == 'Foo'
    assert foos.url_prefix == '/foos'
    assert foos.name == 'Foo'


def test_schema_extra_fields():
    """Ensures that validation doesn't let extra non-defined fields."""

    class FooSchema(Schema):
        foo = Integer()

    foos = FooSchema()

    assert foos.load({'foo': 1}) == {'foo': 1}
    with pytest.raises(ValidationError):
        # var doesn't exist in the schema
        foos.load({'foo': 2, 'bar': 'no!'})


def test_schema_non_writable():
    """Ensures that the user does not upload readonly fields."""

    class FooSchema(Schema):
        foo = Integer(dump_only=True)
        bar = Integer()

    foos = FooSchema()

    with pytest.raises(ValidationError, message={'id': ['Non-writable field']}):
        foos.load({'foo': 1, 'bar': 2})

    # Correctly submit without the value
    foos.load({'bar': 2})
    # Dump is not affected by this validation
    foos.dump({'foo': 1, 'bar': 2})


def test_model_dump(db: SQLAlchemy):
    """Tests ``db.Model.dump()``."""

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        bar = db.Column(db.Integer())

    foo = Foo(id=1)
    result = foo.dump()
    assert result == {'id': 1, 'bar': None}


def test_schema_jsonify(db: SQLAlchemy, app: Teal):
    """Tests ``Schema.jsonify()``."""
    with app.test_request_context():
        class FooSchema(Schema):
            id = Integer()

        foos = FooSchema()

        class Foo(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        foo = Foo(id=1)

        result = foos.jsonify(foo)
        assert json.loads(result.data.decode()) == {'id': 1}


def test_nested_on(fconfig: Config, db: SQLAlchemy):
    """Tests the NestedOn marshmallow field."""
    DeviceDef, ComponentDef, ComputerDef = fconfig.RESOURCE_DEFINITIONS

    class GraphicCard(ComponentDef.SCHEMA):
        speed = Integer()

    class GraphicCardDef(ComponentDef):
        SCHEMA = GraphicCard

    fconfig.RESOURCE_DEFINITIONS += (GraphicCardDef,)

    app = Teal(config=fconfig, db=db)

    pc_template = {
        'id': 1,
        'components': [
            {'id': 2, 'type': 'Component'},
            {'id': 3, 'type': 'GraphicCard', 'speed': 4}
        ]
    }
    with app.app_context():
        schema = app.resources['Computer'].schema
        result = schema.load(pc_template)
        assert pc_template == result
        # Let's add the graphic card's speed field to the component
        with pytest.raises(ValidationError, message={'components': {'speed': ['Unknown field']}}):
            pc = deepcopy(pc_template)
            pc['components'][0]['speed'] = 4
            schema.load(pc)
        # Let's remove the 'type'
        with pytest.raises(ValidationError,
                           message={
                               'components': ['\'Type\' field required to disambiguate resources.']
                           }):
            pc = deepcopy(pc_template)
            del pc['components'][0]['type']
            del pc['components'][1]['type']
            schema.load(pc)
        # Let's set a 'type' that is not a Component
        with pytest.raises(ValidationError,
                           message={'components': ['Computer is not a sub-type of Component']}):
            pc = deepcopy(pc_template)
            pc['components'][0]['type'] = 'Computer'
            schema.load(pc)
