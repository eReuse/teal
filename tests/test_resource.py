from copy import deepcopy

import pytest
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from marshmallow.fields import Integer
from sqlalchemy import Column

from teal.auth import Auth
from teal.config import Config
from teal.db import POLYMORPHIC_ID, POLYMORPHIC_ON
from teal.resource import Resource, Schema, View, url_for_resource
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
    assert foos.SCHEMA().t == foos.type == 'Foo'
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


def test_url_for_resource(app: Teal):
    with app.test_request_context():
        # Note we need a test_request_context or flask won't know
        # which base_url to use.
        assert url_for_resource('Computer') == '/computers/'
        assert url_for_resource('Computer', 24) == '/computers/24'


def test_resource_without_path(config: Config, db: SQLAlchemy):
    """Test resources that don't have url_prefix."""

    class FooDef(Resource):
        VIEW = View
        __type__ = 'Foo'

        def __init__(self, app,
                     import_name=__name__.split('.')[0],
                     static_folder=None,
                     static_url_path=None,
                     template_folder=None,
                     url_prefix='',  # We set url_prefix to empty string
                     subdomain=None,
                     url_defaults=None,
                     root_path=None):
            super().__init__(app, import_name, static_folder, static_url_path, template_folder,
                             url_prefix, subdomain, url_defaults, root_path)

    config.RESOURCE_DEFINITIONS = FooDef,

    app = Teal(config=config, db=db)
    with app.test_request_context():
        assert url_for_resource(FooDef) == '/'
        assert url_for_resource(FooDef, 1) == '/1'


def test_init_db(db: SQLAlchemy, config: Config):
    """Tests :meth:`teal.resource.Resource.init_db`."""

    class Foo(db.Model):
        id = Column(db.Integer, primary_key=True)

    class FooDef(Resource):
        __type__ = 'Foo'

        def init_db(self, db: SQLAlchemy):
            db.session.add(Foo())

    config.RESOURCE_DEFINITIONS = FooDef,
    app = Teal(config=config, db=db)
    with app.app_context():
        app.init_db()
    with app.app_context():
        # If no commit happened in init_db() or anything else
        # this would not exist
        assert Foo.query.filter_by(id=1).one()

    # Test again but executing init-db through the command-line
    runner = app.test_cli_runner()
    runner.invoke(args=['init-db'], catch_exceptions=False)
    with app.app_context():
        assert Foo.query.filter_by(id=2).one()

    # Test with --erase option
    runner.invoke(args=['init-db', '--erase'], catch_exceptions=False)
    with app.app_context():
        assert Foo.query.count() == 1


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


def test_nested_on(fconfig: Config, db: SQLAlchemy):
    """Tests the NestedOn marshmallow field."""
    DeviceDef, ComponentDef, ComputerDef = fconfig.RESOURCE_DEFINITIONS

    class GraphicCardSchema(ComponentDef.SCHEMA):
        speed = Integer()

    class GraphicCard(ComponentDef.MODEL):
        speed = db.Column(db.Integer)

    class GraphicCardDef(ComponentDef):
        SCHEMA = GraphicCardSchema
        MODEL = GraphicCard

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
        schema = app.resources['Computer'].SCHEMA()
        result = schema.load(pc_template)
        assert pc_template['id'] == result['id']
        assert isinstance(result['components'][0], ComponentDef.MODEL)
        assert isinstance(result['components'][1], GraphicCardDef.MODEL)
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
