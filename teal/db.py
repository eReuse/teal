from typing import Type

from flask_sqlalchemy import Model as _Model, SQLAlchemy
from sqlalchemy.orm import Query
from werkzeug.exceptions import NotFound


class ResourceNotFound(NotFound):
    """The resource does not exist."""

    def __init__(self, collection: str, _id: object) -> None:
        super().__init__('The {} {} doesn\'t exist.'.format(collection, _id))


class Model(_Model):
    # Just provide typing
    query_class = None  # type: Type[Query]
    query = None  # type: Query


db = SQLAlchemy(model_class=Model)
