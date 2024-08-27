from config import get_system_settings

import lib.data as dlib
# from lib.data.sql.SQLConnection import SQLConnection

try:
    import psycopg2
except:
    pass

# DB_SETTINGS = get_db_settings()  # Setup proper config

class PostgreSQLDatabase(dlib.ABCDatabase):
    """PostgreSQL implementation of the ABCDatabase class."""
    pass

