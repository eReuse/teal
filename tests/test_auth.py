from base64 import b64encode
from unittest.mock import MagicMock

from flask.json import jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import Unauthorized

from teal.auth import TokenAuth
from teal.config import Config
from teal.resource import Resource, Schema, View
from teal.teal import Teal


def test_token_auth_view(db: SQLAlchemy):
    """
    Ensures that an authorization endpoint correctly protects against
    wrong credentials (this case tokens), allowing the endpoint
    to only specific cases.
    """

    class TestTokenAuth(TokenAuth):
        authenticate = MagicMock(side_effect=Unauthorized)

    class FooSchema(Schema):
        pass

    class FooView(View):
        get = MagicMock(side_effect=lambda id: jsonify({'did': 'it!'}))

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    class FooDef(Resource):
        SCHEMA = FooSchema
        VIEW = FooView
        MODEL = Foo
        AUTH = True

    class TestConfig(Config):
        RESOURCE_DEFINITIONS = [FooDef]

    app = Teal(config=TestConfig(), Auth=TestTokenAuth, db=db)
    client = app.test_client()

    # No token
    # No auth header sent
    client.get(res=FooSchema.t, status=Unauthorized)
    assert TestTokenAuth.authenticate.call_count == 0

    # Wrong format
    # System couldn't parse Auth header
    client.get(res=FooSchema.t, token='this is wrong', status=Unauthorized)
    assert TestTokenAuth.authenticate.call_count == 0

    # Wrong credentials
    # System can parse credentials but they are incorrect
    client.get(res=FooSchema.t, token=b64encode(b'nok:').decode(), status=Unauthorized)
    # Authenticate method was hit
    assert TestTokenAuth.authenticate.call_count == 1

    # OK
    # Our authenticate method now returns some dummy user instead of
    # raising Unauthorized
    TestTokenAuth.authenticate = MagicMock(return_value={'id': '1'})
    data, _ = client.get(res=FooSchema.t, token=b64encode(b'ok:').decode())
    TestTokenAuth.authenticate.assert_called_once_with('ok', '')
    # The endpoint was hit
    assert data == {'did': 'it!'}
    FooView.get.assert_called_once_with(id=None)
