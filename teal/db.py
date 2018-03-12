from typing import Iterator

import pymongo.collection as pycol
from bson import ObjectId
from flask_pymongo import PyMongo
from werkzeug.exceptions import NotFound

from teal import resource as res


class Database(PyMongo):
    pass


class ResourceNotFound(NotFound):
    """The resource does not exist."""

    def __init__(self, collection: str, _id: object) -> None:
        super().__init__('The {} {} doesn\'t exist.'.format(collection, _id))


class Collection:
    def __init__(self, collection: str, db: Database, schema: 'res.Schema') -> None:
        self.db = db
        self.collection_name = collection
        self.schema = schema
        """This schema can be the second one, if any."""

    def one(self, _id: ObjectId or str, **kwargs) -> dict:
        """Find one resource or throw an exception."""
        resource = self.col.find_one(_id, **kwargs)
        if not resource:
            raise ResourceNotFound(self.col.name, _id)
        return self._load(resource)

    def find(self, query_filter: dict, **kwargs) -> Iterator[dict]:
        """Find many or zero resources."""
        cursor = self.col.find(query_filter, **kwargs)
        for resource in cursor:
            yield self._load(resource)

    def _load(self, resource):
        return self.schema.load(resource)

    @property
    def col(self) -> pycol.Collection:
        """
        The mongo collection.

        Accessing this values requires an active app context.
        """
        return self.db.db[self.collection_name]
