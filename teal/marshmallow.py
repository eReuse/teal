from distutils.version import StrictVersion
from typing import Type

from boltons.typeutils import issubclass
from flask import current_app
from marshmallow import ValidationError, utils
from marshmallow.fields import Field, Nested as MarshmallowNested, missing_

from teal.db import SQLAlchemy, Model
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


class NestedOn(MarshmallowNested):
    def __init__(self,
                 nested,
                 polymorphic_on: str,
                 default=missing_,
                 exclude=tuple(),
                 only=None,
                 db: SQLAlchemy = None,
                 **kwargs):
        """

        :param polymorphic_on: The field name that discriminates
                               the type of object. For example ``type``.
                               Then ``type`` contains the class name
                               of a subschema of ``nested``.
        """
        self.polymorphic_on = polymorphic_on
        if only:
            assert isinstance(only, list)
        assert isinstance(polymorphic_on, str)
        super().__init__(nested, default, exclude, only, **kwargs)
        self.db = db

    def _deserialize(self, value, attr, data):
        if self.many and not utils.is_collection(value):
            self.fail('type', input=value, type=value.__class__.__name__)

        if isinstance(self.only, str):  # self.only is a field name
            if self.many:
                value = [{self.only: v} for v in value]
            else:
                value = {self.only: value}
        # New code:
        parent_schema = current_app.resources[super().schema.t].SCHEMA
        if self.many:
            return [self._deserialize_one(single, parent_schema, attr) for single in value]
        else:
            return self._deserialize_one(value, parent_schema, attr)

    def _deserialize_one(self, value, parent_schema: Type[Schema], attr):
        if self.polymorphic_on not in value:
            raise ValidationError('\'Type\' field required to disambiguate resources.',
                                  field_names=[attr])
        type = value[self.polymorphic_on]
        resource = current_app.resources[type]
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
        model = self.db.Model._decl_class_registry.data[value.pop('type')]() # type: Model
        assert issubclass(model, Model)
        return model(**value)


