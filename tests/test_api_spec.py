from teal.client import Client


def test_apispec(client: Client):
    """Tests the output of Apispec"""
    api, _ = client.get('/apidocs')
    assert 'Computer' in api['definitions']
    assert 'Component' in api['definitions']
    assert 'Device' in api['definitions']
    # Ensure resources have endpoints
    assert set(api['paths'].keys()) == {
        '/computers/',
        '/components/',
        '/devices/',
        '/apidocs'
    }
