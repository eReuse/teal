"""
Tests resources on the app level
"""
from typing import Tuple
from unittest.mock import MagicMock

import pytest
from flask import Response, request
from flask.json import jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow.fields import Integer
from werkzeug.exceptions import MethodNotAllowed, NotFound, UnprocessableEntity

from teal.client import Client
from teal.config import Config
from teal.marshmallow import IsType, ValidationError
from teal.resource import Resource as ResourceDef
from teal.teal import Teal
from tests.conftest import populated_db


def test_init(app: Teal):
    """
    Tests the initialization of resources with their relationships
    and inheritance.
    """
    DeviceDef, ComponentDef, ComputerDef = \
        app.config['RESOURCE_DEFINITIONS']  # type: Tuple[ResourceDef]
    assert isinstance(app.resources['Device'], DeviceDef)
    assert isinstance(app.resources['Computer'], ComputerDef)
    assert isinstance(app.resources['Component'], ComponentDef)
    assert app.tree['Device'].parent is None
    assert app.tree['Computer'] in app.tree['Device'].descendants
    assert app.tree['Component'] in app.tree['Device'].descendants
    assert len(app.tree['Device'].descendants) == 2
    assert app.tree['Computer'].parent == app.tree['Component'].parent == app.tree['Device']

    views = {
        'Component.main',
        'Computer.main',
        'Device.main',
        'apidocs_endpoint',
        'static'
    }
    assert views == set(app.view_functions.keys())


def test_models(app: Teal, db: SQLAlchemy):
    """Checks that the models used in the fixture work."""
    DeviceDef, ComponentDef, ComputerDef = \
        app.config['RESOURCE_DEFINITIONS']  # type: Tuple[ResourceDef]
    Component = ComponentDef.MODEL
    Computer = ComputerDef.MODEL

    component = Component(id=1, model='foo')
    pc = Computer(id=2, model='bar', components=[component])
    with app.app_context():
        db.session.add(pc)
        queried_pc = Computer.query.first()
        assert pc == queried_pc


def test_validator_is_type(app: Teal):
    """Checks the validator IsType"""
    with app.app_context():
        is_type = IsType()
        is_type('Device')
        is_type('Component')
        with pytest.raises(ValidationError):
            is_type('Foo')

        is_subtype = IsType('Component')
        is_subtype('Component')
        with pytest.raises(ValidationError):
            is_subtype('Computer')


def test_inheritance_access(fconfig: Config, db: SQLAlchemy):
    """
    Tests that the right endpoint is called when accessing sub-resources.
    """
    DeviceDef, ComponentDef, ComputerDef = fconfig.RESOURCE_DEFINITIONS  # type: Tuple[ResourceDef]

    DUMMY_DICT = {'ok': 'yes'}

    def foo(*args, **kw):
        return jsonify(DUMMY_DICT)

    DeviceDef.VIEW.get = MagicMock(side_effect=foo)
    ComponentDef.VIEW.get = MagicMock(side_effect=foo)
    ComputerDef.VIEW.get = MagicMock(side_effect=foo)

    client = Teal(config=fconfig, db=db).test_client()  # type: Client

    # Access any non-defined URI
    client.get(uri='/this-does-not-exist', status=NotFound)
    assert DeviceDef.VIEW.get.call_count == \
           ComponentDef.VIEW.get.call_count == \
           ComputerDef.VIEW.get.call_count == 0

    # Access to a non-defined method for a resource
    client.post(res=DeviceDef.type, status=MethodNotAllowed, data=dict())
    assert DeviceDef.VIEW.get.call_count == \
           ComponentDef.VIEW.get.call_count == \
           ComputerDef.VIEW.get.call_count == 0

    # Get top resource Device
    # Only device endpoint is called
    d, _ = client.get(res=DeviceDef.type)
    assert d == DUMMY_DICT
    DeviceDef.VIEW.get.assert_called_once_with(id=None)
    assert ComponentDef.VIEW.get.call_count == 0
    assert ComputerDef.VIEW.get.call_count == 0

    # Get computer
    # Only component endpoint is called
    d, _ = client.get(res=ComputerDef.type)
    assert d == DUMMY_DICT
    assert DeviceDef.VIEW.get.call_count == 1  # from before
    assert ComponentDef.VIEW.get.call_count == 0
    ComputerDef.VIEW.get.assert_called_once_with(id=None)


def test_post(fconfig: Config, db: SQLAlchemy):
    """
    Tests posting resources, going through API (Marshmallow) and DB
    (SQLAlchemy) validation, and retrieving and returning a result.
    """
    DeviceDef, ComponentDef, ComputerDef = fconfig.RESOURCE_DEFINITIONS  # type: Tuple[ResourceDef]
    Computer = ComputerDef.MODEL
    Component = ComponentDef.MODEL
    PC = {
        'id': 1,
        'model': 'foo',
        'components': [{'id': 2, 'type': 'Component'}, {'id': 3, 'type': 'Component'}]
    }

    def post():
        pc = request.get_json()
        pc = Computer(**pc)
        db.session.add(pc)
        db.session.commit()
        return Response(status=201)

    def _one(id):
        pc = Computer.query.filter_by(id=id).first()
        return_pc = {
            'id': pc.id,
            'model': pc.model,
            'type': pc.type,
        }
        # todo convert components to JSON
        return return_pc

    def one(id: int):
        return jsonify(_one(id))

    def find(_):
        return jsonify([_one(1)])

    ComputerDef.VIEW.post = MagicMock(side_effect=post)
    ComputerDef.VIEW.one = MagicMock(side_effect=one)
    ComputerDef.VIEW.find = MagicMock(side_effect=find)

    app = Teal(config=fconfig, db=db)

    client = app.test_client()  # type: Client
    with populated_db(db, app):
        client.post(res=ComputerDef.type, data=PC)
        # Wrong data
        data, _ = client.post(res=ComputerDef.type, data={'id': 'foo'}, status=ValidationError)
        assert data == {
            'code': 422,
            'type': 'ValidationError',
            'message': {'id': ['Not a valid integer.']}
        }
        # Get the first data
        data, _ = client.get(res=ComputerDef.type, item=1)
        assert data == {'id': 1, 'model': 'foo', 'type': 'Computer'}
        # Get all data
        data, _ = client.get(res=ComputerDef.type)
        assert data == [{'id': 1, 'model': 'foo', 'type': 'Computer'}]


def test_item_path(fconfig: Config, db: SQLAlchemy):
    """
    Tests that the URL converter works for the item endpoints of
    the resources.

    The following test has set an URL converter of type int, and will
    allow only integers using the flask rules.
    """
    DeviceDef, *_ = fconfig.RESOURCE_DEFINITIONS  # type: Tuple[ResourceDef, ...]

    def cannot_find(id):
        assert id == 1
        return Response(status=200)

    DeviceDef.VIEW.one = MagicMock(side_effect=cannot_find)
    app = Teal(config=fconfig, db=db)
    client = app.test_client()  # type: Client
    with populated_db(db, app):
        # All ok, we expect an int and got an int
        client.get(res=DeviceDef.type, item=1)
        DeviceDef.VIEW.one.assert_called_once_with(1)
        # Conversion of 'int' works in here
        client.get(res=DeviceDef.type, item='1')
        assert DeviceDef.VIEW.one.call_count == 2
        # Anything else fails and our function is directly not executed
        client.get(res=DeviceDef.type, item='foo', status=NotFound)
        assert DeviceDef.VIEW.one.call_count == 2


def test_args(fconfig: Config, db: SQLAlchemy):
    """Tests the handling of query arguments in the URL."""
    DeviceDef, *_ = fconfig.RESOURCE_DEFINITIONS  # type: Tuple[ResourceDef]

    class FindArgsFoo(DeviceDef.VIEW.FindArgs):
        foo = Integer()

    DeviceDef.VIEW.FindArgs = FindArgsFoo

    def find(args: dict):
        assert args == {'foo': 25}
        return Response(status=200)

    DeviceDef.VIEW.find = MagicMock(side_effect=find)

    client = Teal(config=fconfig, db=db).test_client()  # type: Client

    # Ok
    client.get(res=DeviceDef.type, query=[('foo', 25)])
    # Extra not needed data
    client.get(res=DeviceDef.type, query=[('foo', 25), ('bar', 'nope')])
    # Wrong data
    r, _ = client.get(res=DeviceDef.type, query=[('foo', 'nope')], status=UnprocessableEntity)
    # todo r should contain descriptive message of why it fails


def test_http_exception(fconfig: Config, db: SQLAlchemy):
    """Tests correct handling of HTTP exceptions."""
    DeviceDef, *_ = fconfig.RESOURCE_DEFINITIONS  # type: Tuple[ResourceDef]

    DeviceDef.VIEW.get = MagicMock(side_effect=NotFound)
    client = Teal(config=fconfig, db=db).test_client()  # type: Client
    d, _ = client.get(res=DeviceDef.type, status=NotFound)
    assert d == {
        'code': 404,
        'message': 'The requested URL was not found on the server.  '
                   'If you entered the URL manually please check your spelling and try again.',
        'type': 'NotFound'
    }
