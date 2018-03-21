import json

import pytest
from marshmallow import ValidationError
from marshmallow.fields import Nested

from teal.config import Config
from teal.fields import Natural
from teal.teal import Teal
from teal.tests.client import Client
from ereuse_utils.test import ANY
from teal.tests.conftest import Device, DeviceDef, DeviceView, TestTokenAuth


class Component(Device):
    """Component with a reference to the computer where it is in."""
    parent = Natural()  # Only the ID


class ComponentView(DeviceView):
    pass


class Computer(Device):
    """Computer with a nested list of components."""
    components = Nested(Component, many=True)  # All the component info


class ComputerView(DeviceView):
    pass


class ComputerDef(DeviceDef):
    RESOURCE_VIEW = ComputerView
    SCHEMA = Computer
    MODEL = Computer
    AUTH = True


class ComponentDef(DeviceDef):
    RESOURCE_VIEW = ComponentView
    SCHEMA = Component
    MODEL = Component
    AUTH = False


class TestConfig(Config):
    RESOURCE_DEFINITIONS = [DeviceDef, ComputerDef, ComponentDef]
    DATABASE = 'foo'


@pytest.fixture()
def app() -> Teal:
    return Teal(config=TestConfig(db='foo', mongo_db='teal_foo'), Auth=TestTokenAuth)


def test_nested(app: Teal):
    """
    Tests two nested resources that inherit from the same schema.

    The ``Computer`` contains multiple ``Component``.
    """
    computer = app.resources['Computer'].schema
    with pytest.raises(ValidationError):
        computer.load({
            'serial_number': '1',
            'components': [{'serial_number': '5'}, {'serial_number': 3}]  # SN must be a number
        })
    computer.loads(json.dumps({
        'serial_number': '5',
        'components': [{'serial_number': '5'}, {'model': 'foo'}]
    }))


def test_swagger(client: Client):
    """Tests the output of Swagger with Flasgger."""
    api, _ = client.get('/apispec_1.json')
    assert 'Computer' in api['definitions']
    assert 'Component' in api['definitions']
    assert 'Car' not in api['definitions']
    assert 'Device' in api['definitions']
    assert 'Device' in api['definitions']
    # todo this should be exactly equal but flassger duplicates 'definition'?
    assert api['definitions']['Computer']['properties']['components']['items'][
               'properties'].keys() == api['definitions']['Component']['properties'].keys()
    # Ensure resources have endpoints
    assert set(api['paths'].keys()) == {
        '/computers/', '/components/{id}', '/computers/{id}',
        '/components/', '/devices/{id}', '/devices/'
    }, 'Components, devices and computers are the only allowed paths'
    # Computer endpoint is secured but not Component
    assert 'security' in api['paths']['/computers/']['post']
    assert api['paths']['/computers/']['post']['security']['type'] == 'http', \
        'Computer endpoint must be secured as it has Auth'
    assert 'security' not in api['paths']['/components/']['post'], \
        'Component endpoint must not be secured'
    html, _ = client.get('/apidocs/', accept=ANY)
    assert '<body class="swagger-section">' in html, 'The HTML must be swagger page'
