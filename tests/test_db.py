from distutils.version import StrictVersion

import pytest
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import NotFound

from teal.db import StrictVersionType
from teal.teal import Teal


def test_not_found(app: Teal):
    """
    When not finding a resource, the db should raise a ``NotFound``
    exception instead of the built-in for SQLAlchemy.
    """
    with app.app_context():
        Device = app.resources['Device'].MODEL
        with pytest.raises(NotFound):
            Device.query.one()


def test_db_default_column_name(db: SQLAlchemy):
    """Ensures that the default column name is snake case (default)."""

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    assert Foo.__tablename__ == 'foo'

    class FooBar(db.Model):
        id = db.Column(db.Integer, primary_key=True)

    assert FooBar.__tablename__ == 'foo_bar'


def test_db_psql_schemas(db: SQLAlchemy):
    """Tests multiple psql schemas."""
    # todo do this


def test_db_strict_version_type(db: SQLAlchemy):
    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        bar = db.Column(StrictVersionType)

    foo = Foo(id=1, bar=StrictVersion('1.0.0a1'))
    assert isinstance(foo.bar, StrictVersion)
