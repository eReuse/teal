from boltons.urlutils import URL
from ereuse_utils.test import Client as EreuseUtilsClient, JSON
from flask import Response
from werkzeug.exceptions import HTTPException


class Client(EreuseUtilsClient):
    """A REST interface to a Teal app."""

    def open(self, uri: str, res: str = None, status: int or HTTPException = 200, accept=JSON,
             content_type=JSON, item=None, headers: dict = None, token: str = None, **kw) \
            -> (dict or str, Response):
        headers = headers or {}
        if res:
            resource_url = self.application.resources[res].url_prefix + '/'
            uri = URL(uri).navigate(resource_url).to_text()
        if token:
            headers['Authorization'] = 'Basic {}'.format(token)
        return super().open(uri, status, accept, content_type, item, headers, **kw)

    def get(self, uri: str = '', res: str = None, query: dict = {},
            status: int or HTTPException = 200, item=None, accept: str = JSON,
            headers: dict = None, token: str = None, **kw) -> (dict or str, Response):
        """
        Performs GET.

        :param uri: The uri where to GET from. This is optional, as you
                    can build the URI too through ``res`` and ``item``.
        :param res: The resource where to GET from, if any.
                    If this is set, the client will try to get the
                    url from the resource definition.
        :param query: The query params in a dict. This method
                      automatically converts the dict to URL params,
                      and if the dict had nested dictionaries, those
                      are converted to JSON.
        :param status: A status code or exception to assert.
        :param item: The id of a resource to GET from, if any.
        :param accept: The accept headers. By default
                       ``application/json``.
        :param headers: A dictionary of header name - header value.
        :param token: A token to add to an ``Authentication`` header.
        :return: A tuple containing 1. a dict (if content-type is JSON)
                 or a str with the data, and 2. the ``Response`` object.
        """
        kw['res'] = res
        kw['token'] = token
        return super().get(uri, query, item, status, accept, headers, **kw)

    def post(self, data: str or dict, uri: str = '', res: str = None,
             status: int or HTTPException = 201, content_type: str = JSON, accept: str = JSON,
             headers: dict = None, token: str = None,
             **kw) -> (dict or str, Response):
        kw['res'] = res
        kw['token'] = token
        return super().post(uri, data, status, content_type, accept, headers, **kw)

    def patch(self, data: str or dict, uri: str = '', res: str = None,
              item=None, status: int or HTTPException = 200, content_type: str = JSON,
              accept: str = JSON, token: str = None,
              headers: dict = None, **kw) -> (dict or str, Response):
        kw['res'] = res
        kw['token'] = token
        return super().patch(uri, data, status, content_type, item, accept, headers, **kw)

    def post_get(self, res: str, data: str or dict, status: int or HTTPException = 201,
                 content_type: str = JSON, accept: str = JSON, headers: dict = None,
                 key='id', token: str = None, **kw) \
            -> (dict or str, Response):
        """Performs post and then gets the resource through its key."""
        r, _ = self.post('', data, res, status, content_type, accept, token, headers, **kw)
        return self.get(res=res, item=r[key])
