from marshmallow.fields import Integer, Number


class RangedNumber(Number):
    """
    A number between ``min`` and up to but not including ``max``.

    Don't set `min`` or ``max`` to have unlimited bottom or top range,
    respectively.
    """
    default_error_messages = {
        'range': 'Number is not between range.'
    }

    def __init__(self, min: float = None, max: float = None, **kwargs):
        assert min is not None or max is not None, 'You have not set neither min or max.'
        self.min = min
        self.max = max
        kwargs['minimum'] = min
        kwargs['maxiumum'] = max
        kwargs['type'] = 'integer'
        super().__init__(**kwargs)

    def _format_num(self, value):
        number = super()._format_num(value)
        if self.min is not None and number < self.min or \
                self.max is not None and number >= self.max:
            self.fail('range')
        return number

    def _jsonschema_type_mapping(self):
        return {
            'type': 'rangedNumber',
        }


class Natural(RangedNumber, Integer):
    """
    A natural number is a positive int. Optionally you can set a
    ``max``, which ensures the number is up to but not including
    ``max``.
    """
    default_error_messages = {
        'invalid': 'Not a valid Natural number.'
    }

    def __init__(self, min: int = 0, max: int = None):
        assert min >= 0, 'Min can\'t be a negative if represents a Natural.'
        super().__init__(min=min, max=max, strict=True)

    def _jsonschema_type_mapping(self):
        return {
            'type': 'natural',
        }
