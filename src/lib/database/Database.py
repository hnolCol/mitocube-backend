from config.settings.db import get_db_settings
from lib.database.abstract.Database import DatabaseABC

DB_SETTINGS = get_db_settings()


class _LazyDB:
    """
    Transparent proxy around the concrete database.

    Instantiating the real database opens a Neo4j connection, which used to
    happen at import time in every module holding ``DB = Database.DB()``.
    The proxy defers that connection until the first attribute access so the
    whole application (and its test suite) can be imported without a running
    database.
    """

    __slots__ = ("_instance",)

    def __init__(self):
        self._instance = None

    def _resolve(self):
        if self._instance is None:
            from lib.database.neo4j.Database import DB
            self._instance = DB
        return self._instance

    def __getattr__(self, name):
        return getattr(self._resolve(), name)


class Database:

    @staticmethod
    def DB() -> DatabaseABC:
        return _shared_lazy_db


_shared_lazy_db = _LazyDB()
