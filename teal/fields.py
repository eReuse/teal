from marshmallow.fields import Number
from pydash import in_range


class RangedNumber(Number):
    """
    A number between ``min`` and up to but not including ``max``.

    Don't set `min`` or ``max`` to have unlimited bottom or top range,
    respectively.
    """
    default_error_messages = {
        'range': 'Number is not between range.'
    }

    def __init__(self, as_string=False, min: int = None, max: int = None, **kwargs):
        self.min = min
        self.max = max
        kwargs['minimum'] = min
        kwargs['maxiumum'] = max
        kwargs['type'] = 'integer'
        super().__init__(as_string, **kwargs)

    def _format_num(self, value):
        number = super()._format_num(value)
        if not in_range(number, self.min, self.max):
            self.fail('range')

    def _jsonschema_type_mapping(self):
        return {
            'type': 'rangedNumber',
        }


class Natural(RangedNumber):
    """
    A natural number is a positive int. Optionally you can set a
    ``max``, which ensures the number is up to but not including
    ``max``.
    """
    num_type = int
    default_error_messages = {
        'invalid': 'Not a valid natural'
    }

    def __init__(self, as_string=False, max: int = None, **kwargs):
        super().__init__(as_string, 0, max, **kwargs)

    def _jsonschema_type_mapping(self):
        return {
            'type': 'natural',
        }
