from enum import Enum
from typing import Callable, Iterable, Tuple, Type

from boltons.typeutils import classproperty
from ereuse_utils.naming import Naming
from flasgger import SwaggerView
from flask import Blueprint, request
from flask.json import jsonify
from marshmallow import Schema as MarshmallowSchema, SchemaOpts as MarshmallowSchemaOpts, \
    ValidationError, validates_schema
from webargs.flaskparser import parser
from werkzeug.exceptions import MethodNotAllowed

from teal.auth import Auth
from teal.db import Model


class SchemaOpts(MarshmallowSchemaOpts):
    """
    Subclass of Marshmallow's SchemaOpts that provides
    options for Teal's schemas.
    """

    def __init__(self, meta, ordered=False):
        super().__init__(meta, ordered)
        self.PREFIX = meta.PREFIX


class Schema(MarshmallowSchema):
    """
    The definition of the fields of a resource.
    """
    OPTIONS_CLASS = SchemaOpts

    class Meta:
        PREFIX = None
        """Optional. A prefix for the type; ex. devices:Computer."""

    # noinspection PyMethodParameters
    @classproperty
    def t(cls: Type['Schema']) -> str:
        """The type for this schema, auto-computed from its name."""
        name, *_ = cls.__name__.split('Schema')
        return Naming.new_type(name, cls.Meta.PREFIX)

    # noinspection PyMethodParameters
    @classproperty
    def resource(cls: Type['Schema']) -> str:
        """The resource name of this schema."""
        return Naming.resource(cls.t)

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, _, original_data: dict):
        """
        Raises a validationError when user sends extra fields.

        From `Marshmallow docs<http://marshmallow.readthedocs.io/en/
        latest/extending.html#validating-original-input-data>`_.
        """
        unknown_fields = set(original_data) - set(f.data_key or n for n, f in self.fields.items())
        if unknown_fields:
            raise ValidationError('Unknown field', unknown_fields)

    @validates_schema(pass_original=True)
    def check_dump_only(self, _, orig_data: dict):
        """
        Raises a ValidationError if the user is submitting
        'read-only' fields.
        """
        # Note that validates_schema does not execute when dumping
        dump_only_fields = (name for name, field in self.fields.items() if field.dump_only)
        non_writable = set(orig_data).intersection(dump_only_fields)
        if non_writable:
            raise ValidationError('Non-writable field', non_writable)

    def jsonify(self, model: Model, many: bool = False, update_fields: bool = True, **kw):
        dictionary = model.dump()
        return jsonify(self.dump(dictionary, many, update_fields, **kw))


class View(SwaggerView):
    """
    A REST interface for resources.
    """

    class FindArgs(MarshmallowSchema):
        """
        Allowed arguments for the ``find``
        method (GET collection) endpoint
        """

    def __init__(self, definition: 'Resource', **kw) -> None:
        self.resource_def = definition
        """The ResourceDefinition tied to this view."""
        self.schema = definition.schema
        """The schema tied to this view."""
        super().__init__()

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        definition = class_kwargs['definition']  # type: Resource
        cls.definitions = {
            # todo if we use the SCHEMA.type instead of the name
            # flassger doesn't match it with the respones.200.schema
            # below and dies
            definition.SCHEMA.__name__: definition.SCHEMA
        }
        """
        Input parameters, through body or in the URL query. You can
        override them in each endpoint like we do in :meth:`.get` 
        """
        cls.responses = {
            200: {
                'description': 'A Schema.',
                'schema': definition.SCHEMA
            }
        }
        """
        The default response for these endpoints. You can override
        it per endpoint.
        """
        if definition.AUTH:
            auth = class_kwargs['auth']  # type: Auth
            cls.security = auth.SWAGGER
            """The security endpoint for this view."""
        return super().as_view(name, *class_args, **class_kwargs)

    def get(self, id):
        """
        Get a collection of resources or a specific one.

        ---
        parameters:
          - name: id
            in: path
            description: The identifier of the resource.
        """
        if id:
            response = self.one(id)
        else:
            args = parser.parse(self.FindArgs(), request, locations={'querystring'})
            response = self.find(args)
        return response

    def one(self, id):
        """GET one specific resource (ex. /cars/1)."""
        raise MethodNotAllowed()

    def find(self, args: dict):
        """GET a list of resources (ex. /cars)."""
        raise MethodNotAllowed()

    def post(self):
        raise MethodNotAllowed()

    def delete(self, id):
        raise MethodNotAllowed()

    def put(self, id):
        raise MethodNotAllowed()

    def patch(self, id):
        raise MethodNotAllowed()


class Converters(Enum):
    """An enumeration of available URL converters."""
    string = 'string'
    int = 'int'
    float = 'float'
    path = 'path'
    any = 'any'
    uid = 'uuid'


class Resource(Blueprint):
    """
    Main resource class. Defines the schema, views,
    authentication, database and collection of a resource.

    A ``ResourceDefinition`` is a Flask
    :class:`flask.blueprints.Blueprint` that provides everything
    needed to set a REST endpoint.
    """
    VIEW = View  # type: Type[View]
    """Resource view linked to this definition."""
    SCHEMA = Schema  # type: Type[Schema]
    """The Schema that validates a submitting resource at the entry point."""
    AUTH = False
    """
    If true, authentication is required for all the endpoints of this 
    resource defined in ``VIEW``.
    """
    ID_NAME = 'id'
    """
    The variable name for GET *one* operations that is used as an id.
    """
    ID_CONVERTER = Converters.string
    """
    The converter for the id.

    Note that converters do **cast** the value, so the converter 
    ``uuid`` will return an ``UUID`` object.
    """

    def __init__(self, app,
                 import_name=__package__,
                 static_folder=None,
                 static_url_path=None,
                 template_folder=None,
                 url_prefix=None,
                 subdomain=None,
                 url_defaults=None,
                 root_path=None,
                 cli_commands: Iterable[Tuple[Callable, str or None]] = tuple()):
        self.schema = self.SCHEMA()
        name = self.schema.t
        url_prefix = url_prefix or '/{}'.format(self.resource)
        super().__init__(name, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path)
        self.app = app
        # Views
        view = self.VIEW.as_view('main', definition=self, auth=app.auth)
        if self.AUTH:
            view = app.auth.requires_auth(view)
        self.add_url_rule('/', defaults={'id': None}, view_func=view, methods={'GET'})
        self.add_url_rule('/', view_func=view, methods={'POST'})
        self.add_url_rule('/<{}:{}>'.format(self.ID_CONVERTER.value, self.ID_NAME),
                          view_func=view, methods={'GET', 'PUT', 'DELETE'})
        self.cli_commands = cli_commands

    @classproperty
    def type(cls):
        return cls.SCHEMA.t

    @classproperty
    def resource(cls):
        return cls.SCHEMA.resource
