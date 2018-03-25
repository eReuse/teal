import pytest
from werkzeug.exceptions import NotFound

from teal.teal import Teal


def test_not_found(app: Teal):
    """
    When not finding a resource, the db should raise a ``NotFound``
    exception instead of the built-in for SQLAlchemy.
    """
    with app.test_request_context():
        Device = app.resources['Device'].MODEL
        with pytest.raises(NotFound):
            Device.query.one()
