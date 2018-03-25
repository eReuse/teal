from typing import Dict, List, Type

from boltons.typeutils import issubclass
from boltons.urlutils import URL

from teal import resource


class Config:
    """
    The configuration class.

    Subclass and set here your config values.
    """
    RESOURCE_DEFINITIONS = []  # type: List[Type['resource.ResourceDefinition']]
    """
    A list of resource definitions to load.
    """

    SQLALCHEMY_DATABASE_URI = None  # type: str
    """
    The access to the main Database.
    """
    SQLALCHEMY_BINDS = {}  # type: Dict[str, str]
    """
    Optional extra databases. See `here <http://flask-sqlalchemy.pocoo.org
    /2.3/binds/#referring-to-binds>`_ how bind your models to different
    databases.
    """
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    """
    Disables flask-sqlalchemy notification system. 
    Save resources and hides a warning by flask-sqlalchemy itself.
    
    See `this answer in Stackoverflow for more info
    <https://stackoverflow.com/a/33790196>`_. 
    """

    SWAGGER = {
        'info': {
            'title': 'Teal API',
        }
    }
    """
    Swagger definition object. Use values from `here <https://github.com
    /rochacbruno/flasgger#initializing-flasgger-with-default-data>`_ 
    """

    def __init__(self, db: str = None) -> None:
        """
        :param db: Optional. Set the ``SQLALCHEMY_DATABASE_URI`` param.
        """
        assert all(issubclass(r, resource.ResourceDefinition) for r in self.RESOURCE_DEFINITIONS)
        if db:
            assert URL(db), 'Set a valid URI'
            self.SQLALCHEMY_DATABASE_URI = db
