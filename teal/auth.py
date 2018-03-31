from functools import wraps
from typing import Callable

from flask import current_app, g, request
from werkzeug.exceptions import Unauthorized


class Auth:
    """
    Authentication handler for Teal.

    To authenticate the user (perform login):
    1. Set Resource.AUTH to True, or manually decorate the view with
      @auth.requires_auth
    2. Extend any subclass of this one (like TokenAuth).
    3. Implement the authenticate method with the authentication logic.
       For example, in TokenAuth here you get the user from the token.
    5. Set in your teal the Auth class you have created so
       teal can use it.
    """

    SWAGGER = {
        'type': 'http',
        'description:': 'HTTP Basic scheme',
        'name': 'Authorization',
        'in': 'header',
        'scheme': 'basic'
    }

    @classmethod
    def requires_auth(cls, f: Callable):
        """
        Decorate a view enforcing authentication (logged in user).
        """

        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth:
                raise Unauthorized('Provide proper authorization credentials')
            current_app.auth.perform_auth(auth)
            return f(*args, **kwargs)

        return decorated

    def perform_auth(self, auth):
        """
        Authenticate an user. This loads the user.

        An exception (expected Unauthorized) is raised if
        authentication failed.
        """
        g.account = self.authenticate(auth.username, auth.password)

    def authenticate(self, username: str, password: str) -> object:
        """
        The authentication logic. The result of this method is
        a user or a raised exception, like Werkzeug's Unauthorized,
        if authentication failed.

        :raise: Unauthorized Authentication failed.
        :return: A tuple with the user_id and the user object.
        """
        raise NotImplementedError()


class TokenAuth(Auth):
    SWAGGER = Auth.SWAGGER.copy()
    SWAGGER['description'] = 'Basic scheme with token.'

    def authenticate(self, token: str, *args, **kw) -> object:
        """
        The result of this method is
        a user or a raised exception if authentication failed.

        :raise: Unauthorized Authentication failed.
        :return A tuple with the user_id and the user object.
        """
        raise NotImplementedError()