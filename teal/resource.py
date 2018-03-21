from enum import Enum
from typing import Type

from boltons.typeutils import classproperty
from ereuse_utils.naming import Naming
from flasgger import SwaggerView
from flask import Blueprint
from marshmallow import Schema as MarshmallowSchema, SchemaOpts as MarshmallowSchemaOpts

from teal.auth import Authentication
from teal.db import Collection, Database


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
    def type(cls: Type['Schema']) -> str:
        """The type for this schema, auto-computed from its name."""
        name = cls.mro()[1].__name__ if 'Model' in cls.__name__ else cls.__name__
        return Naming.new_type(name, cls.Meta.PREFIX)

    # noinspection PyMethodParameters
    @classproperty
    def resource(cls: Type['Schema']) -> str:
        """The resource name of this schema."""
        return Naming.resource(cls.type)


class ResourceView(SwaggerView):
    """
    A REST interface for resources.
    """

    def __init__(self, definition: 'ResourceDefinition', **kwargs) -> None:
        self.resource_def = definition
        """The ResourceDefinition tied to this view."""
        self.collection = definition.collection
        """The Mongo collection tied to this view."""
        super().__init__()

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        definition = class_kwargs['definition']  # type: ResourceDefinition
        cls.definitions = {
            definition.SCHEMA.type: definition.SCHEMA
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
            auth = class_kwargs['auth']  # type: Authentication
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
            response = self.find()
        return response

    def one(self, id):
        """GET one specific resource (ex. /cars/1)."""
        return self.collection.one(id)

    @Authentication.requires_auth
    def find(self):
        """GET a list of resources (ex. /cars)."""
        # todo pagination, sorting
        return self.collection.find({})

    def post(self):
        pass

    def delete(self, id):
        pass

    def put(self, id):
        pass

    def patch(self, id):
        pass


class Converters(Enum):
    """An enumeration of available URL converters."""
    string = 'string'
    int = 'int'
    float = 'float'
    path = 'path'
    any = 'any'
    uid = 'uuid'


class ResourceDefinition(Blueprint):
    """
    Main resource class. Defines the schema, views,
    authentication, database and collection of a resource.

    A ``ResourceDefinition`` is a Flask
    :class:`flask.blueprints.Blueprint` that provides everything
    needed to set a REST endpoint.
    """
    RESOURCE_VIEW = ResourceView  # type: Type[ResourceView]
    """Resource view linked to this definition."""
    SCHEMA = Schema  # type: Type[Schema]
    """The Schema that validates a submitting resource at the entry point."""
    USE_COMMON_DB = None  # type: bool
    """Database to use. If none then the default database is used.
     Only meaningful when using multiple databases."""
    COLLECTION = None  # type: str or None
    """Mandatory. The name of a collection to use."""
    MODEL = None  # type: Type[Schema]
    """
    A schema that validates a submitting resource before saving 
    it into the db.
    """
    AUTH = False
    """
    If true, authentication is required for ALL the endpoints of this 
    resource.
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

    def __init__(self, db: Database, common_db: Database, auth: Authentication,
                 import_name=__package__, name=None, static_folder=None,
                 static_url_path=None, template_folder=None, url_prefix=None, subdomain=None,
                 url_defaults=None, root_path=None):
        assert self.COLLECTION, 'Have you defined collection?'
        name = name or self.__class__.__name__
        url_prefix = url_prefix or '/{}'.format(self.resource)
        super().__init__(name, import_name, static_folder, static_url_path, template_folder,
                         url_prefix, subdomain, url_defaults, root_path)
        db = common_db if self.USE_COMMON_DB else db
        self.schema = self.SCHEMA()
        self.model = self.MODEL()
        self.collection = Collection(self.COLLECTION, db, getattr(self, 'db_schema', 'schema'))
        # Views
        view = self.RESOURCE_VIEW.as_view('main', **{'definition': self, 'auth': auth})
        if self.AUTH:
            view = auth.requires_auth(view)
        self.add_url_rule('/', defaults={'id': None}, view_func=view, methods={'GET'})
        self.add_url_rule('/', view_func=view, methods={'POST'})
        self.add_url_rule('/<{}:{}>'.format(self.ID_CONVERTER.value, self.ID_NAME),
                          view_func=view, methods={'GET', 'PUT', 'DELETE'})

    @classproperty
    def type(cls):
        return cls.SCHEMA.type

    @classproperty
    def resource(cls):
        return cls.SCHEMA.resource
