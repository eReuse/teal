from distutils.version import StrictVersion
from typing import Type

from flask import current_app as app, g
from marshmallow import utils
from marshmallow.fields import Field, Nested as MarshmallowNested, \
    ValidationError as _ValidationError, missing_
from marshmallow.validate import Validator
from marshmallow_enum import EnumField as _EnumField

from teal.db import Model, SQLAlchemy
from teal.resource import Schema


class Version(Field):
    """A python StrictVersion field, like '1.0.1'."""

    def _serialize(self, value, attr, obj):
        return str(value) if value is not None else None

    def _deserialize(self, value, attr, data):
        return StrictVersion(value) if value is not None else None


class Color(Field):
    """Any color field that can be accepted by the colour package."""

    def _serialize(self, value, attr, obj):
        return str(value) if value is not None else None

    def _deserialize(self, value, attr, data):
        from colour import Color
        return Color(value) if value is not None else None


class URL(Field):
    def _serialize(self, value, attr, obj):
        return value.to_text() if value is not None else None

    def _deserialize(self, value, attr, data):
        return URL(value) if value is not None else None


class NestedOn(MarshmallowNested):
    """
    A relationship with a resource schema that emulates the
    relationships in SQLAlchemy.

    When deserializing values this instantiates a SQLAlchemy Model
    that fits the value in ``polymorphic_on``, usually named ``type``.

    When serializing from :meth:`teal.resource.Schema.jsonify` it
    serializes nested relationships up to a defined limit.
    """
    NESTED_LEVEL = '_level'
    NESTED_LEVEL_MAX = '_level_max'

    def __init__(self,
                 nested,
                 polymorphic_on: str,
                 db: SQLAlchemy,
                 collection_class=list,
                 default=missing_,
                 exclude=tuple(),
                 only=None,
                 **kwargs):
        """

        :param polymorphic_on: The field name that discriminates
                               the type of object. For example ``type``.
                               Then ``type`` contains the class name
                               of a subschema of ``nested``.
        """
        self.polymorphic_on = polymorphic_on
        self.collection_class = collection_class
        assert isinstance(polymorphic_on, str)
        assert isinstance(only, str) or only is None
        super().__init__(nested, default, exclude, only, **kwargs)
        self.db = db

    def _deserialize(self, value, attr, data):
        if self.many and not utils.is_collection(value):
            self.fail('type', input=value, type=value.__class__.__name__)

        if isinstance(self.only, str):  # self.only is a field name
            if self.many:
                value = self.collection_class({self.only: v} for v in value)
            else:
                value = {self.only: value}
        # New code:
        parent_schema = app.resources[super().schema.t].SCHEMA
        if self.many:
            return self.collection_class(self._deserialize_one(single, parent_schema, attr)
                                         for single in value)
        else:
            return self._deserialize_one(value, parent_schema, attr)

    def _deserialize_one(self, value, parent_schema: Type[Schema], attr):
        if self.polymorphic_on not in value:
            raise ValidationError('\'Type\' field required to disambiguate resources.',
                                  field_names=[attr])
        type = value[self.polymorphic_on]
        resource = app.resources[type]
        if not issubclass(resource.SCHEMA, parent_schema):
            raise ValidationError('{} is not a sub-type of {}'.format(type, parent_schema.t),
                                  field_names=[attr])
        schema = resource.SCHEMA(only=self.only,
                                 exclude=self.exclude,
                                 context=getattr(self.parent, 'context', {}),
                                 load_only=self._nested_normalized_option('load_only'),
                                 dump_only=self._nested_normalized_option('dump_only'))
        schema.ordered = getattr(self.parent, 'ordered', False)
        value = schema.load(value)
        model = self.db.Model._decl_class_registry.data[type]()  # type: Model
        assert issubclass(model, Model)
        return model(**value)

    def serialize(self, attr: str, obj, accessor=None) -> dict:
        """See class docs."""
        if g.get(NestedOn.NESTED_LEVEL) == g.get(NestedOn.NESTED_LEVEL_MAX):
            # Idea from https://marshmallow-sqlalchemy.readthedocs.io
            # /en/latest/recipes.html#smart-nested-field
            # Gets the FK of the relationship instead of the full object
            # This won't work for many-many relationships (as they are lists)
            # In such case return None
            # todo is this the behaviour we want?
            return getattr(obj, attr + '_id', None)
        setattr(g, NestedOn.NESTED_LEVEL, g.get(NestedOn.NESTED_LEVEL) + 1)
        ret = super().serialize(attr, obj, accessor)
        setattr(g, NestedOn.NESTED_LEVEL, g.get(NestedOn.NESTED_LEVEL) - 1)
        return ret


class IsType(Validator):
    """
    Validator which succeeds if the value it is passed is a registered
    resource type.

    :param parent: If set, type must be a subtype of such resource.
                   By default accept any resource.
    """
    # todo remove if not needed
    no_type = 'Type does not exist.'
    no_subtype = 'Type is not a descendant type of {parent}'

    def __init__(self, parent: str = None) -> None:
        self.parent = parent  # type: str

    def _repr_args(self):
        return 'parent={0!r}'.format(self.parent)

    def __call__(self, type: str):
        assert not self.parent or self.parent in app.resources
        try:
            r = app.resources[type]
            if self.parent:
                if not issubclass(r.__class__, app.resources[self.parent].__class__):
                    raise ValidationError(self.no_subtype.format(self.parent))
        except KeyError:
            raise ValidationError(self.no_type)


class ValidationError(_ValidationError):
    code = 422


class EnumField(_EnumField):
    """
    An EnumField that allows
    generating OpenApi enums through Apispec.
    """
    def __init__(self, enum, by_value=False, load_by=None, dump_by=None, error='', *args,
                 **kwargs):
        super().__init__(enum, by_value, load_by, dump_by, error, *args, **kwargs)
        self.metadata['enum'] = [e.name for e in enum]
