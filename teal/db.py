from distutils.version import StrictVersion
from typing import Type

from flask_sqlalchemy import Model as _Model, SQLAlchemy as FlaskSQLAlchemy, SignallingSession
from sqlalchemy import event, inspect, types
from sqlalchemy.orm import Query as _Query, sessionmaker
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

    def dump(self) -> dict:
        """
        Super simple way of creating a dictionary.

        It doesn't handle recursion nor advanced patterns.

        `See this to know how this method can screw it up easily
        <https://bitbucket.org/zzzeek/sqlalchemy/issues/3976/
        built-in-way-to-convert-an-orm-object-ie>`_.
        """
        mapper = inspect(self.__class__)
        return {column.key: getattr(self, column.key) for column in mapper.attrs}


class SchemaSession(SignallingSession):
    """
    Session that is configured to use a PostgreSQL's Schema.

    Idea from `here <https://stackoverflow.com/a/9299021>`_.
    """

    def __init__(self, db, autocommit=False, autoflush=True, **options):
        super().__init__(db, autocommit, autoflush, **options)
        SCHEMA = self.app.config['SCHEMA']
        if SCHEMA:
            self.execute('SET search_path TO {}, public'.format(SCHEMA))


class SQLAlchemy(FlaskSQLAlchemy):
    """
    Controls SQLAlchemy integration with Teal.

    Enhances :class:`flask_sqlalchemy.SQLAlchemy` by using PostgreSQL's
    schemas when creating/dropping tables.

    See :attr:`teal.config.SCHEMA` for more info.
    """

    def __init__(self, app=None, use_native_unicode=True, session_options=None, metadata=None,
                 query_class=Query, model_class=Model):
        super().__init__(app, use_native_unicode, session_options, metadata, query_class,
                         model_class)
        # The following listeners set psql's search_path to the correct
        # schema and create the schemas accordingly

        # Specifically:
        # 1. Creates the schemas and set ``search_path`` to app's config SCHEMA
        event.listen(self.metadata, 'before_create', self.create_schemas)
        # Set ``search_path`` to default (``public``)
        event.listen(self.metadata, 'after_create', self.revert_connection)
        # Set ``search_path`` to app's config SCHEMA
        event.listen(self.metadata, 'before_drop', self.set_search_path)
        # Set ``search_path`` to default (``public``)
        event.listen(self.metadata, 'after_drop', self.revert_connection)

    def _execute_for_all_tables(self, app, bind, operation, skip_tables=False):
        # todo how to pass app to our event listeners without contaminating self?
        self._app = self.get_app(app)
        super()._execute_for_all_tables(app, bind, operation, skip_tables)

    def create_schemas(self, target, connection, **kw):
        """
        Create the schemas and set the active schema.

        From `here <https://bitbucket.org/zzzeek/sqlalchemy/issues/3914/
        extend-create_all-drop_all-to-include#comment-40129850>`_.
        """
        schemas = set(table.schema for table in target.tables.values() if table.schema)
        if self._app.config['SCHEMA']:
            schemas.add(self._app.config['SCHEMA'])
        for schema in schemas:
            connection.execute('CREATE SCHEMA IF NOT EXISTS {}'.format(schema))
        self.set_search_path(target, connection)

    def set_search_path(self, _, connection, **kw):
        if self._app.config['SCHEMA']:
            connection.execute('SET search_path TO {}, public'.format(self._app.config['SCHEMA']))

    def revert_connection(self, _, connection, **kw):
        connection.execute('SET search_path TO public')

    def create_session(self, options):
        """As parent's create_session but adding our SchemaSession."""
        return sessionmaker(class_=SchemaSession, db=self, **options)


class StrictVersionType(types.TypeDecorator):
    impl = types.Unicode

    def process_bind_param(self, value, dialect):
        return str(value)

    def process_result_value(self, value, dialect):
        return StrictVersion(value)
