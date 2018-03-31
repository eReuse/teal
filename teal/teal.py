import inspect
from typing import Dict, Iterable, Tuple, Type

from anytree import Node
from ereuse_utils import ensure_utf8
from flasgger import Swagger
from flask import Flask, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from marshmallow_jsonschema import JSONSchema
from werkzeug.exceptions import HTTPException, UnprocessableEntity
from werkzeug.wsgi import DispatcherMiddleware

from teal.auth import Auth
from teal.client import Client
from teal.config import Config as ConfigClass
from teal.db import db as database
from teal.request import Request
from teal.resource import Resource


class Teal(Flask):
    """
    An opinionated REST and JSON first server built on Flask using
    MongoDB and Marshmallow.
    """
    test_client_class = Client
    request_class = Request

    def __init__(self, config: ConfigClass, db: SQLAlchemy = database, import_name=__package__,
                 static_path=None, static_url_path=None, static_folder='static',
                 template_folder='templates', instance_path=None, instance_relative_config=False,
                 root_path=None, Auth: Type[Auth] = Auth):
        ensure_utf8(self.__class__.__name__)
        super().__init__(import_name, static_path, static_url_path, static_folder, template_folder,
                         instance_path, instance_relative_config, root_path)
        self.config.from_object(config)
        # Load databases
        self.auth = Auth()
        self.load_resources()
        self.register_error_handler(HTTPException, self._handle_standard_error)
        self.register_error_handler(ValidationError, self._handle_validation_error)
        self.swag = Swagger(self)
        self.add_url_rule('/schemas', view_func=self.view_schemas, methods={'GET'})
        self.json_schema = JSONSchema()
        db.init_app(self)

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
            resource_def = ResourceDef(self.auth)
            self.register_blueprint(resource_def)
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

    @staticmethod
    def _get_exc_class_and_code(exc_class_or_code):
        # We enforce Flask to allow us to handle HTTPExceptions
        exc_class, _ = super(Teal, Teal)._get_exc_class_and_code(exc_class_or_code)
        return exc_class, None

    def view_schemas(self):
        """Return all schemas in custom JSON Schema format."""
        # todo decide if finally use this
        schemas = {
            r.schema.type: self.json_schema.dump(r.schema).data
            for r in self.resources.values()
        }
        return jsonify(schemas)


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
    default = App(config=Config())
    apps = {
        '/{}'.format(db): App(config=Config(db=sql_uri))
        for db, sql_uri in databases
    }
    return DispatcherMiddleware(default, apps)
