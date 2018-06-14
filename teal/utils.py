from typing import Dict, Tuple

from sqlalchemy.dialects import postgresql


def compiled(Model, query) -> Tuple[str, Dict[str, str]]:
    """
    Generates a SQL statement.

    :return A tuple with 1. the SQL statement and 2. the params for it.
    """
    c = Model.query.filter(*query).statement.compile(dialect=postgresql.dialect())
    return str(c), c.params
