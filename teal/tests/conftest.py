from contextlib import contextmanager

import pytest
from flask_sqlalchemy import SQLAlchemy
from marshmallow.fields import Nested, Str

from teal.config import Config
from teal.db import INHERIT_COND, Model, POLYMORPHIC_ID, POLYMORPHIC_ON
from teal.fields import Natural
from teal.resource import Converters, Resource, Schema, View
from teal.teal import Teal
from teal.tests.client import Client


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
        id = Natural(min=1)
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
        foo = Str()

    class ComponentDef(DeviceDef):
        SCHEMA = ComponentSchema
        VIEW = ComponentView
        MODEL = Component

    class ComputerSchema(DeviceSchema):
        components = Nested(ComponentSchema, many=True)

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
    db.create_all(app=app)
    yield app
    db.drop_all(app=app)


@pytest.fixture()
def client(app: Teal) -> Client:
    return app.test_client()


@contextmanager
def populated_db(db: SQLAlchemy, app: Teal):
    db.create_all(app=app)
    try:
        yield
    finally:
        db.drop_all(app=app)
