from ereuse_utils import JSONEncoder
from flask.json import JSONEncoder as FlaskJSONEncoder


class TealJSONEncoder(JSONEncoder, FlaskJSONEncoder):
    pass
