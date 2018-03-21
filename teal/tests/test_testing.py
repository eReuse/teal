from base64 import b64encode

import pytest
from pymongo.database import Database
from werkzeug.exceptions import Unauthorized

from teal.auth import TokenAuth
from teal.teal import Teal, prefixed_database_factory
from teal.tests.client import Client
from teal.tests.conftest import Car, CarDef, CarModel, Device, DeviceDef, DeviceModel, \
    TestConfig, TestDatabaseFactory, TestTokenAuth


@pytest.fixture()
def app() -> Teal:
    return Teal(config=TestConfig(db='foo', mongo_db='teal_foo'), Auth=TestTokenAuth)


def test_schema():
    """Initializes two schemas with inheritance."""
    device_schema = Device()
    device_model = DeviceModel()
    car_schema = Car()
    car_model = CarModel()
    assert device_schema.type == device_model.type == 'Device'
    assert car_schema.type == car_model.type == 'Car'
    assert car_schema.Meta == car_model.Meta == device_model.Meta


def test_resource_def_init(foo_db: Database):
    """Tests initializing a resource."""
    car_def = CarDef(foo_db, foo_db, TokenAuth())
    assert car_def.schema.type == 'Car'
    assert car_def.model.type == 'Car'


def test_init_app(app: Teal):
    """Inits the app and resources."""
    assert isinstance(app.resources['Device'], DeviceDef)
    assert isinstance(app.resources['Car'], CarDef)
    assert app.tree['Device'].parent is None
    assert app.tree['Device'].descendants == (app.tree['Car'],)
    assert app.tree['Car'].parent == app.tree['Device']

    views = {
        'flasgger.static',  # flasgger stuff
        'flasgger.apidocs',
        'flasgger.apispec_1',
        'flasgger.<lambda>',
        'DeviceDef.main',  # resource view for device
        'CarDef.main',  # resource view for car
        'static',  # flask's default static endpoint
        'view_schemas'  # json schema-like views
    }
    assert views == set(app.view_functions.keys())


def test_get(client: Client):
    """Test basic GET operations"""

    # Get endpoint
    data, _ = client.get(res=Device.type)
    assert data == {'many-foo': 'bar'}

    # Get item in endpoint
    data, _ = client.get(res=Device.type, item=15)
    assert data == {'foo': 'bar'}


def test_auth_view(client: Client):
    """Tests accessing a view that requires authorization."""
    # Get to a non-auth endpoint
    client.get(res=Device.type, item=15, status=200)
    # Let's perform GET with an auth endpoint
    # No token
    client.get(res=Car.type, item=20, status=Unauthorized)
    # Wrong format
    client.get(res=Car.type, item=20, token='wrong format', status=Unauthorized)
    # Wrong credentials
    client.get(res=Car.type, item=20, token=b64encode(b'nok:').decode(), status=Unauthorized)
    # OK
    data, _ = client.get(res=Car.type, item=20, token=b64encode(b'ok:').decode())
    assert data == {'doors': 4, 'id': 20}


def test_prefixed_database_factory():
    """Tests using the database factory middleware."""
    db_factory = TestDatabaseFactory()
    apps = prefixed_database_factory(TestConfig, db_factory.dbs(), Teal)
    assert isinstance(apps.app, Teal)
    assert all(isinstance(app, Teal) for app in apps.mounts.values())
    # todo perform GET or something
