from typing import Type

from flask_sqlalchemy import Model as _Model
from sqlalchemy.orm import Query as _Query
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound


class ResourceNotFound(NotFound):
    """The resource does not exist."""

    # todo show id
    def __init__(self, resource: str) -> None:
        super().__init__('The {} doesn\'t exist.'.format(resource))


POLYMORPHIC_ID = 'polymorphic_identity'
POLYMORPHIC_ON = 'polymorphic_on'
INHERIT_COND = 'inherit_condition'
CASCADE = 'save-update, delete'
CASCADE_OWN = '{}, delete-orphan'.format(CASCADE)


class Query(_Query):
    def one(self):
        try:
            return super().one()
        except NoResultFound:
            raise ResourceNotFound(self._entities)


class Model(_Model):
    # Just provide typing
    query_class = Query  # type: Type[Query]
    query = None  # type: Query
