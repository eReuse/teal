from ereuse_utils import JSONEncoder
from flask.json import JSONEncoder as FlaskJSONEncoder
from sqlalchemy.ext.baked import Result
from sqlalchemy.orm import Query


class TealJSONEncoder(JSONEncoder, FlaskJSONEncoder):

    def default(self, obj):
        if isinstance(obj, (Result, Query)):
            return tuple(obj)
        return super().default(obj)
