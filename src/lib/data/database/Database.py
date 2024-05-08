



from config.settings.db import get_db_settings
from lib.data.database.ABCDatabase import DatabaseABC

DB_SETTINGS = get_db_settings()

class Database:
    
    @staticmethod
    def DB() -> DatabaseABC:
        if DB_SETTINGS.db_handler == "neo4j" or DB_SETTINGS.db_handler =="pandafiles":
            from lib.data.database.Neo4JDatabase import DB as Neo4JDB
            return Neo4JDB