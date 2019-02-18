import enum
import ipaddress
import json
from distutils.version import StrictVersion

import pytest
from boltons import urlutils
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import StatementError
from werkzeug.exceptions import NotFound

from teal.db import DBError, IP, IntEnum, StrictVersionType, URL, UniqueViolation
from teal.teal import Teal
from tests import conftest


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


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_db_strict_version_type(db: SQLAlchemy):
    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        bar = db.Column(StrictVersionType)

    db.create_all()
    foo = Foo(id=1, bar=StrictVersion('1.0.0a1'))
    assert isinstance(foo.bar, StrictVersion)
    db.session.add(foo)
    db.session.commit()


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_db_url(db: SQLAlchemy):
    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        bar = db.Column(URL)

    db.create_all()
    foo = Foo(id=1, bar=urlutils.URL('http://foo.com/bar'))
    assert foo.bar == urlutils.URL('http://foo.com/bar')
    db.session.add(foo)
    db.session.commit()


def test_db_ip():
    # We cannot actually try this on the db as we use sqlite for testing
    ip = IP()
    x = ip.process_bind_param(ipaddress.ip_address('192.168.1.1'), None)
    assert x == '192.168.1.1'
    y = ip.process_result_value('192.168.1.1', None)
    assert str(y) == '192.168.1.1'


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_db_int_enum(db: SQLAlchemy):
    class FooEnum(enum.IntEnum):
        foo = 1
        bar = 2

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        bar = db.Column(IntEnum(FooEnum))

    db.create_all()
    foo = Foo(id=1, bar=FooEnum.foo)
    assert FooEnum.foo == foo.bar
    db.session.add(foo)
    db.session.flush()

    # Add something that is not the IntEnum
    bar = Foo(id=2, bar=2)
    db.session.add(bar)
    with pytest.raises(StatementError):
        db.session.flush()


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_db_error():
    normal = DBError(Exception())
    assert normal.__class__ == DBError
    e = Exception('UNIQUE constraint "foo"')
    e.params = {
        'foo': 'bar'
    }
    unique = DBError(e)
    assert unique.__class__ == UniqueViolation
    e = json.loads(jsonify(unique).data)
    assert e['message'] == 'UNIQUE constraint "foo"'
    assert e['constraint'] == 'foo'
    assert e['fieldName'] == 'foo'
    assert e['fieldValue'] == 'bar'
    assert e['type'] == 'UniqueViolation'
    assert e['code'] == 400


@pytest.mark.usefixtures(conftest.app_context.__name__)
def test_db_error_unique_violation(db: SQLAlchemy):
    """UniqueViolation"""

    class Foo(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        unique = db.Column(db.Integer, unique=True)

    db.create_all()
    foo = Foo(id=1, unique=1)
    db.session.add(foo)
    db.session.commit()
    foo_again = Foo(id=2, unique=1)
    db.session.add(foo_again)
    with pytest.raises(UniqueViolation):
        db.session.commit()
