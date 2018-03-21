import pytest
from flask.json import jsonify
from marshmallow import fields as m_fields
from marshmallow.fields import DateTime
from pymongo import MongoClient
from werkzeug.exceptions import Unauthorized

from teal import fields
from teal.auth import TokenAuth
from teal.config import Config, DatabaseFactory
from teal.db import Database
from teal.fields import RangedNumber
from teal.resource import Converters, ResourceDefinition, ResourceView, Schema
from teal.teal import Teal
from teal.tests.client import Client


class DeviceView(ResourceView):
    def one(self, id):
        assert id == 15
        return jsonify({'foo': 'bar'})

    def find(self):
        return jsonify({'many-foo': 'bar'})

    def post(self):
        """
        Posts a Device.
        ---
        parameters:
            - name: device
              in: body
              description: The device to create.
              schema:
                $ref: "#/definitions/Device"
        """
        super().post()


class Device(Schema):
    id = RangedNumber(min=0)
    serial_number = m_fields.Str()
    model = m_fields.Str()
    manufacturer = m_fields.Str()
    created = DateTime(description='When it was created.')
    updated = DateTime(description='When it was updated.')


class DeviceModel(Device):
    pass


class DeviceDef(ResourceDefinition):
    RESOURCE_VIEW = DeviceView
    SCHEMA = Device
    MODEL = DeviceModel
    COLLECTION = 'devices'
    ID_CONVERTER = Converters.int


class Car(Device):
    doors = fields.Natural()


class CarModel(Car):
    license_plate = m_fields.Str()


class CarView(ResourceView):
    def one(self, id):
        assert id == 20
        return jsonify({'id': 20, 'doors': 4})


class CarDef(DeviceDef):
    RESOURCE_VIEW = CarView
    SCHEMA = Car
    MODEL = CarModel
    AUTH = True


class TestConfig(Config):
    RESOURCE_DEFINITIONS = [DeviceDef, CarDef]
    DATABASE = 'foo'


class TestTokenAuth(TokenAuth):

    def authenticate(self, token: str, *args, **kw) -> object:
        if token == 'ok':
            return {'id': 'user'}
        else:
            raise Unauthorized()


@pytest.fixture()
def client(app: Teal) -> Client:
    return app.test_client()


@pytest.fixture()
def mongo_client():
    return MongoClient()


@pytest.fixture()
def foo_db(mongo_client: MongoClient) -> Database:
    return mongo_client.test_database


class TestDatabaseFactory(DatabaseFactory):
    DATABASES = {'foo', 'bar'}
    MONGO_DB_PREFIX = 'tteal_'
