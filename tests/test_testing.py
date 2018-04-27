from distutils.version import StrictVersion

from flask import json

from teal.config import Config
from teal.teal import Teal, prefixed_database_factory


def test_prefixed_database_factory():
    """Tests using the database factory middleware."""
    dbs = ('foo', 'sqlite:////tmp/foo.db'), ('bar', 'sqlite:////tmp/bar.db')
    apps = prefixed_database_factory(Config, dbs, Teal)
    assert isinstance(apps.app, Teal)
    assert all(isinstance(app, Teal) for app in apps.mounts.values())
    # todo perform GET or something


def test_json_encoder(app: Teal):
    """
    Ensures that Teal is using the custom JSON Encoder through Flask's
    json.
    """
    with app.app_context():
        # Try to dump a type flask's json encoder cannot handle
        json.dumps({'foo': StrictVersion('1.3')})
