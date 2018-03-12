from typing import Generator, List, Tuple, Type

from boltons.typeutils import issubclass

from teal import resource


class Config:
    """
    The configuration class.

    Subclass and set here your config values.
    """
    RESOURCE_DEFINITIONS = []  # type: List[Type['resource.ResourceDefinition']]
    """
    A list of resource definitions to load.
    """

    COMMON_DBNAME = 'teal'
    """
    Shared database used with middlewares. Optional. 
    Only useful when using middlewares.
    """

    def __init__(self, db: str = None, mongo_db: str = None) -> None:
        """
        :param mongo_db: Optional. Set the default mongo database.
        """
        assert all(issubclass(r, resource.ResourceDefinition) for r in self.RESOURCE_DEFINITIONS)
        if db:
            self.DATABASE = db
            self.MONGO_DBNAME = mongo_db


class DatabaseFactory:
    """
    Class to generate a mapping suitable for the param ``databases``
    in :py:func:`teal.teal.prefixed_database_factory`.
    """

    DATABASES = {}
    """
    Names of the databases. Needs to be valid URI and mongo database
    characters.
    :py:func:`teal.teal.prefixed_database_factory` makes a teal app for
    each database. Override this with suitable values.
    """
    MONGO_DB_PREFIX = 'teal_'
    """
    An optional prefix to prepend to the name of the databases
    in mongo. Ex. a database named *foo* will be called *teal_foo* in
    mongo.
    """

    def dbs(self) -> Generator[Tuple[str, str], None, None]:
        """
        Returns a mapping suitable for
        :py:func:`teal.teal.prefixed_database_factory`
        """
        for db in self.DATABASES:
            yield db, '{}{}'.format(self.MONGO_DB_PREFIX, db)
