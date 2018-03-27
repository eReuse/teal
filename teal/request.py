from flask import Request as _Request, current_app

from teal import resource as res


class Request(_Request):
    def get_json(self, force=False, silent=False, cache=True, validate=True):
        json = super().get_json(force, silent, cache)
        if validate and self.blueprint in current_app.resources:
            resource_def = current_app.resources[self.blueprint]  # type: res.Resource
            json = resource_def.schema.load(json)
        return json
