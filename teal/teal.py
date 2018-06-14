import inspect
from typing import Dict, Iterable, Tuple, Type

from anytree import Node
from click import option
from ereuse_utils import ensure_utf8
from flasgger import Swagger
from flask import Flask, Response, jsonify
from flask.globals import _app_ctx_stack
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from marshmallow_jsonschema import JSONSchema
from werkzeug.exceptions import HTTPException, UnprocessableEntity
from werkzeug.wsgi import DispatcherMiddleware

from teal.auth import Auth
from teal.client import Client
from teal.config import Config as ConfigClass
from teal.json_util import TealJSONEncoder
from teal.request import Request
from teal.resource import Resource


class Teal(Flask):
    """
    An opinionated REST and JSON first server built on Flask using
    MongoDB and Marshmallow.
    """
    test_client_class = Client
    request_class = Request
    json_encoder = TealJSONEncoder

    def __init__(self,
                 config: ConfigClass,
                 db: SQLAlchemy,
                 import_name=__package__,
                 static_url_path=None,
                 static_folder='static',
                 static_host=None,
                 host_matching=False,
                 subdomain_matching=False,
                 template_folder='templates',
                 instance_path=None,
                 instance_relative_config=False,
                 root_path=None,
                 Auth: Type[Auth] = Auth):
        ensure_utf8(self.__class__.__name__)
        super().__init__(import_name, static_url_path, static_folder, static_host, host_matching,
                         subdomain_matching, template_folder, instance_path,
                         instance_relative_config, root_path)
        self.config.from_object(config)
        # Load databases
        self.auth = Auth()
        self.load_resources()
        self.register_error_handler(HTTPException, self._handle_standard_error)
        self.register_error_handler(ValidationError, self._handle_validation_error)
        self.swag = Swagger(self)
        self.add_url_rule('/schemas', view_func=self.view_schemas, methods={'GET'})
        self.json_schema = JSONSchema()
        self.db = db
        db.init_app(self)
        self.cli.command('init-db')(self.init_db)

    # noinspection PyAttributeOutsideInit
    def load_resources(self):
        self.resources = {}  # type: Dict[str, Resource]
        """
        The resources definitions loaded on this App, referenced by their
        type name.
        """
        self.tree = {}  # type: Dict[str, Node]
        """
        A tree representing the hierarchy of the instances of 
        ResourceDefinitions. ResourceDefinitions use these nodes to
        traverse their hierarchy.
         
        Do not use the normal python class hierarchy as it is global,
        thus unreliable if you run different apps with different
        schemas (for example, an extension that is only added on the
        third app adds a new type of user).
        """
        for ResourceDef in self.config['RESOURCE_DEFINITIONS']:
            resource_def = ResourceDef(self)  # type: Resource
            self.register_blueprint(resource_def)
            for cli_command, *args in resource_def.cli_commands:  # Register CLI commands
                self.cli.command(*args)(cli_command)

            # todo should we use resource_def.name instead of type?
            # are we going to have collisions? (2 resource_def -> 1 schema)
            self.resources[resource_def.type] = resource_def
            self.tree[resource_def.type] = Node(resource_def.type)
        # Link tree nodes between them
        for _type, node in self.tree.items():
            resource_def = self.resources[_type]
            _, Parent, *superclasses = inspect.getmro(resource_def.__class__)
            if Parent is not Resource:
                node.parent = self.tree[Parent.type]

    @staticmethod
    def _handle_standard_error(e: HTTPException):
        """
        Handles HTTPExceptions by transforming them to JSON.
        """
        try:
            data = {'message': e.description, 'code': e.code, 'type': e.__class__.__name__}
        except AttributeError as e:
            return Response(str(e), status=500)
        else:
            response = jsonify(data)
            response.status_code = e.code
            return response

    @staticmethod
    def _handle_validation_error(e: ValidationError):
        data = {
            'message': e.messages,
            'code': UnprocessableEntity.code,
            'type': e.__class__.__name__
        }
        response = jsonify(data)
        response.status_code = UnprocessableEntity.code
        return response

    def view_schemas(self):
        """Return all schemas in custom JSON Schema format."""
        # todo decide if finally use this
        schemas = {
            r.schema.type: self.json_schema.dump(r.schema).data
            for r in self.resources.values()
        }
        return jsonify(schemas)

    @option('--erase/--no-erase', default=False, help='Delete all db contents before?')
    def init_db(self, erase: bool = False):
        """
        Initializes a database from scratch,
        creating tables and needed resources.

        Note that this does not create the database per se.

        If executing this directly, remember to use an app_context.

        Resources can hook functions that will be called when this
        method executes, by subclassing :meth:`teal.resource.
        Resource.load_resource`.
        """
        assert _app_ctx_stack.top, 'Use an app context.'
        if erase:
            self.db.drop_all()
        self.db.create_all()
        for resource in self.resources.values():
            resource.init_db(self.db)
        self.db.session.commit()


def prefixed_database_factory(Config: Type[ConfigClass],
                              databases: Iterable[Tuple[str, str]],
                              App: Type[Teal] = Teal) -> DispatcherMiddleware:
    """
    A factory of Teals. Allows creating as many Teal apps as databases
    from the DefaultConfig.DATABASES, setting each Teal app to an URL in
    the following way:
    - / -> to the Teal app that uses the
      :attr:`teal.config.Config.SQLALCHEMY_DATABASE_URI` set in config.
    - /db1/... -> to the Teal app with db1 as default
    - /db2/... -> to the Teal app with db2 as default
    And so on.

    DefaultConfig is used to configure the root Teal app.
    Optionally, each other app can have a custom Config. Pass them in
    the `configs` dictionary. Apps with no Config will default to the
    DefaultConfig.

    :param Config: The configuration class to use with each database
    :param databases: Names of the databases, where the first value is a
                      valid  URI to use in the dispatcher middleware and
                      the second value the SQLAlchemy URI referring to a
                      database to use.
    :param App: A Teal class.
    :return: A WSGI middleware where an app without database is default
    and the rest prefixed with their database name.
    """
    # todo
    db = SQLAlchemy()
    default = App(config=Config(), db=db)
    apps = {
        '/{}'.format(path_uri): App(config=Config(db=sql_uri), db=db)
        for path_uri, sql_uri in databases
    }
    return DispatcherMiddleware(default, apps)
