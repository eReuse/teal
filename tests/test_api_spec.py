from ereuse_utils.test import ANY, Client
from flask_sqlalchemy import SQLAlchemy

from teal.auth import TokenAuth
from teal.config import Config
from teal.resource import Resource, Schema
from teal.teal import Teal


def test_swagger(client: Client):
    """Tests the output of Swagger with Flasgger."""
    api, _ = client.get('/apispec_1.json')
    assert 'ComputerSchema' in api['definitions']
    assert 'ComponentSchema' in api['definitions']
    assert 'DeviceSchema' in api['definitions']
    # Ensure resources have endpoints
    assert set(api['paths'].keys()) == {
        '/computers/', '/components/{id}', '/computers/{id}',
        '/components/', '/devices/{id}', '/devices/'
    }, 'Components, devices and computers are the only allowed paths'
    html, _ = client.get('/apidocs/', accept=ANY)
    assert 'swagger-ui' in html, 'The HTML must be swagger page'


def test_swagger_auth(db: SQLAlchemy):
    """Tests that swagger recognizes an endpoint with Authorization."""

    class TestTokenAuth(TokenAuth):
        def authenticate(self, token: str, *args, **kw):
            pass

    class FooSchema(Schema):
        pass

    class FooDef(Resource):
        SCHEMA = FooSchema
        AUTH = True

    class TestConfig(Config):
        RESOURCE_DEFINITIONS = [FooDef]

    app = Teal(config=TestConfig(), Auth=TestTokenAuth, db=db)
    client = app.test_client()

    api, _ = client.get('/apispec_1.json')
    # Endpoint is secured
    assert 'security' in api['paths']['/foos/']['post']
    assert api['paths']['/foos/']['post']['security']['type'] == 'http'
