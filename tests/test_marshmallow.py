import ipaddress
from distutils import version

import colour
import pytest
from boltons import urlutils
from marshmallow import Schema, ValidationError as MaValidationError
from sqlalchemy_utils import PhoneNumber, PhoneNumberParseException

from teal import marshmallow
from teal.marshmallow import Phone, SanitizedStr


def test_marshmallow_color():
    class Foo(Schema):
        foo = marshmallow.Color()

    foo = Foo()
    foo.load({'foo': 'blue'})
    # todo pytest raises
    with pytest.raises(ValueError, match='\'this is not a color\' is not a recognized color.'):
        foo.load({'foo': 'this is not a color'})

    serialized = foo.dump({'foo': colour.Color('red')})
    assert serialized == {'foo': 'red'}
    serialized = foo.dump({'foo': None})
    assert serialized == {'foo': None}


def test_marshmallow_version():
    class Foo(Schema):
        foo = marshmallow.Version()

    foo = Foo()
    foo.load({'foo': '1.0.1'})
    with pytest.raises(ValueError, match='invalid version number \'this is not a version\''):
        foo.load({'foo': 'this is not a version'})

    serialized = foo.dump({'foo': version.StrictVersion('1.0.1')})
    assert serialized == {'foo': '1.0.1'}
    serialized = foo.dump({'foo': None})
    assert serialized == {'foo': None}


def test_marshmallow_url():
    class Foo(Schema):
        foo = marshmallow.URL()

    foo = Foo()
    foo.load({'foo': 'https://foo.com/bar'})
    foo.load({'foo': 'https://foo.com/'})
    with pytest.raises(ValueError):
        foo.load({'foo': 'this is not an url'})
    with pytest.raises(ValueError):
        foo.load({'foo': 'foo.com/'})

    serialized = foo.dump({'foo': urlutils.URL('https://foo.com/bar')})
    assert serialized == {'foo': 'https://foo.com/bar'}

    serialized = foo.dump({'foo': None})
    assert serialized == {'foo': None}

    class Bar(Schema):
        bar = marshmallow.URL(require_path=True)

    bar = Bar()
    bar.load({'bar': 'https://foo.com/bar'})
    with pytest.raises(ValueError):
        bar.load({'bar': 'https://foo.com'})
    with pytest.raises(ValueError):
        bar.load({'bar': 'https://foo.com/'})


def test_marshmallow_ip():
    class Foo(Schema):
        foo = marshmallow.IP()

    foo = Foo()
    foo.load({'foo': '192.168.1.1'})
    with pytest.raises(ValueError,
                       match='\'this is not an url\' does not appear to be an IPv4 or IPv6 address'):
        foo.load({'foo': 'this is not an url'})

    serialized = foo.dump({'foo': ipaddress.ip_address('192.168.1.1')})
    assert serialized == {'foo': '192.168.1.1'}

    serialized = foo.dump({'foo': None})
    assert serialized == {'foo': None}


def test_marshmallow_phone():
    class Foo(Schema):
        foo = Phone()

    foo = Foo()
    foo.load({'foo': '+34936666666'})
    with pytest.raises(PhoneNumberParseException):  # Phone number cannot be parsed
        foo.load({'foo': 'this is not a phone number'})

    with pytest.raises(ValueError, match='The phone number is invalid.'):
        # Phone number is invalid for the country rules
        foo.load({'foo': '+3401'})

    serialized = foo.dump({'foo': PhoneNumber('+34936666666')})
    assert serialized == {'foo': '+34 936 66 66 66'}

    serialized = foo.dump({'foo': None})
    assert serialized == {'foo': None}


def test_marshmallow_sanitized_str():
    class Foo(Schema):
        foo = SanitizedStr(lower=True)

    foo = Foo()
    x = foo.load({'foo': 'bar'})
    assert x['foo'] == 'bar'
    x = foo.load({'foo': 'BAr  '})
    assert x['foo'] == 'bar'
    with pytest.raises(MaValidationError):
        foo.load({'foo': '<a>asdf'})
    with pytest.raises(MaValidationError):
        foo.load({'foo': '[0m[1;36mart[46;34mÜ'})
