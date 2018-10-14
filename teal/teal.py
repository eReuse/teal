import inspect
from typing import Dict, Iterable, Tuple, Type

import click_spinner
import flask_cors
from anytree import Node
from apispec import APISpec
from click import option
from ereuse_utils import ensure_utf8
from flask import Flask, Response, jsonify
from flask.globals import _app_ctx_stack
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException, UnprocessableEntity
from werkzeug.wsgi import DispatcherMiddleware

from teal.auth import Auth
from teal.client import Client
from teal.config import Config as ConfigClass
from teal.json_util import TealJSONEncoder
from teal.request import Request
from teal.resource import Converters, LowerStrConverter, Resource


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
                 import_name=__name__.split('.')[0],
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
        flask_cors.CORS(self)
        # Load databases
        self.auth = Auth()
        self.url_map.converters[Converters.lower.name] = LowerStrConverter
        self.load_resources()
        self.register_error_handler(HTTPException, self._handle_standard_error)
        self.register_error_handler(ValidationError, self._handle_validation_error)
        self.db = db
        db.init_app(self)
        self.cli.command('init-db')(self.init_db)
        self.spec = None  # type: APISpec
        self.apidocs()

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
                # todo cli commands with multiple arguments end-up reversed
                # when teal has been executed multiple times (ex. testing)
                # see _param_memo func in click package
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
        print('Initializing database...'.ljust(30), end='')
        with click_spinner.spinner():
            if erase:
                self.db.drop_all()
            self._init_db()
            self.db.session.commit()
        print('done.')

    def _init_db(self):
        """Where the database is initialized. You can override this."""
        self.db.create_all()
        for resource in self.resources.values():
            resource.init_db(self.db)

    def apidocs(self):
        """Apidocs configuration and generation."""
        self.spec = APISpec(
            plugins=(
                'apispec.ext.flask',
                'apispec.ext.marshmallow',
            ),
            **self.config.get_namespace('API_DOC_CONFIG_')
        )
        for name, resource in self.resources.items():
            self.spec.definition(name,
                                 schema=resource.SCHEMA,
                                 extra_fields=self.config.get_namespace('API_DOC_CLASS_'))
        self.add_url_rule('/apidocs', view_func=self.apidocs_endpoint)

    def apidocs_endpoint(self):
        """An endpoint that prints a JSON OpenApi 2.0 specification."""
        if not getattr(self, '_apidocs', None):
            # We are forced to to this under a request context
            for path, view_func in self.view_functions.items():
                if path != 'static':
                    self.spec.add_path(view=view_func)
            self._apidocs = self.spec.to_dict()
        return jsonify(self._apidocs)


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
