from distutils.version import StrictVersion
from re import I
from typing import Tuple
from unittest.mock import MagicMock

import pytest
from flask import Response, current_app, json

from teal.client import Client
from teal.config import Config
from teal.db import SchemaSQLAlchemy
from teal.teal import Teal
from tests import conftest


def test_json_encoder(app: Teal):
    """
    Ensures that Teal is using the custom JSON Encoder through Flask's
    json.
    """
    with app.app_context():
        # Try to dump a type flask's json encoder cannot handle
        json.dumps({'foo': StrictVersion('1.3')})


def test_cors(fconfig: Config, db: SchemaSQLAlchemy):
    DeviceDef, *_ = fconfig.RESOURCE_DEFINITIONS  # type: Tuple[ResourceDef]

    def foo(*args, **kw):
        return Response(status=200)

    DeviceDef.VIEW.get = MagicMock(side_effect=foo)
    client = Teal(config=fconfig, db=db).test_client()  # type: Client
    _, response = client.get('/devices/')
    # NOTE(@slamora): if calling `to_wsgi_list()` is problematic maybe
    # it could be replaced by cast to list
    headers = response.headers.to_wsgi_list()
    assert ('Access-Control-Expose-Headers', 'Authorization') in headers
    assert ('Access-Control-Allow-Origin', '*') in headers


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_regular_error():
    """Tests a regular error that is not dumpeable."""
    try:
        9 / 0
    except Exception as e:
        r = current_app._handle_standard_error(e)
    assert r.json == {
        'code': 500,
        'message': "division by zero",
        'type': 'ZeroDivisionError'
    }
