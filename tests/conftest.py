from contextlib import contextmanager

import pytest
from flask.testing import FlaskCliRunner
from marshmallow.fields import Integer, Str
from marshmallow.validate import Range

from teal.client import Client
from teal.config import Config
from teal.db import INHERIT_COND, Model, POLYMORPHIC_ID, POLYMORPHIC_ON, SQLAlchemy
from teal.marshmallow import NestedOn
from teal.resource import Converters, Resource, Schema, View
from teal.teal import Teal


@pytest.fixture()
def config() -> Config:
    class TestConfig(Config):
        Testing = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SQLALCHEMY_TRACK_MODIFICATIONS = False

    return TestConfig()


@pytest.fixture()
def db():
    return SQLAlchemy(model_class=Model)


@pytest.fixture()
def fconfig(config: Config, db: SQLAlchemy) -> Config:
    return f_config(config, db)


def f_config(config: Config, db: SQLAlchemy) -> Config:
    """
    Creates 3 resources like in the following::

        Device
           |
           |________
          /        |
        Computer Component

    ``Computer`` and ``Component`` inherit from ``Device``, and
    a computer has many components::

        Computer 1 -- * Component
    """

    class DeviceSchema(Schema):
        id = Integer(validate=Range(min=1))
        type = Str()
        model = Str()

    class DeviceView(View):
        pass

    class Device(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        model = db.Column(db.String(80), nullable=True)
        type = db.Column(db.String)

        __mapper_args__ = {
            POLYMORPHIC_ID: 'Device',
            POLYMORPHIC_ON: type
        }

    class DeviceDef(Resource):
        SCHEMA = DeviceSchema
        VIEW = DeviceView
        MODEL = Device
        ID_CONVERTER = Converters.int

    class ComponentSchema(DeviceSchema):
        pass

    class Component(Device):
        id = db.Column(db.Integer, db.ForeignKey(Device.id), primary_key=True)

        parent_id = db.Column(db.Integer, db.ForeignKey('computer.id'))
        parent = db.relationship('Computer',
                                 backref=db.backref('components', lazy=True),
                                 primaryjoin='Component.parent_id == Computer.id')

        __mapper_args__ = {
            POLYMORPHIC_ID: 'Component',
            INHERIT_COND: id == Device.id
        }

    class ComponentView(DeviceView):
        pass

    class ComponentDef(DeviceDef):
        SCHEMA = ComponentSchema
        VIEW = ComponentView
        MODEL = Component

    class ComputerSchema(DeviceSchema):
        components = NestedOn(ComponentSchema, polymorphic_on='type', many=True, db=db)

    class Computer(Device):
        id = db.Column(db.Integer, db.ForeignKey(Device.id), primary_key=True)
        # backref creates a 'parent' relationship in Component

        __mapper_args__ = {
            POLYMORPHIC_ID: 'Computer',
            INHERIT_COND: id == Device.id
        }

    class ComputerView(DeviceView):
        pass

    class ComputerDef(DeviceDef):
        SCHEMA = ComputerSchema
        VIEW = ComputerView
        MODEL = Computer

    config.RESOURCE_DEFINITIONS = DeviceDef, ComponentDef, ComputerDef
    return config


@pytest.fixture()
def app(fconfig: Config, db: SQLAlchemy) -> Teal:
    app = Teal(config=fconfig, db=db)
    with app.app_context():
        app.init_db()
    yield app


@pytest.fixture()
def app_context(app: Teal):
    with app.app_context():
        yield


@pytest.fixture()
def client(app: Teal) -> Client:
    return app.test_client()


@contextmanager
def populated_db(db: SQLAlchemy, app: Teal):
    db.create_all(app=app)
    yield


@pytest.fixture()
def runner(app: Teal) -> FlaskCliRunner:
    return app.test_cli_runner()
