from teal.config import Config
from teal.teal import Teal, prefixed_database_factory


def test_prefixed_database_factory():
    """Tests using the database factory middleware."""
    dbs = ('foo', 'sqlite:////tmp/foo.db'), ('bar', 'sqlite:////tmp/bar.db')
    apps = prefixed_database_factory(Config, dbs, Teal)
    assert isinstance(apps.app, Teal)
    assert all(isinstance(app, Teal) for app in apps.mounts.values())
    # todo perform GET or something
