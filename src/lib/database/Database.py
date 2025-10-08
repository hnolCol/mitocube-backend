



from config.settings.db import get_db_settings
from lib.database.abstract.Database import DatabaseABC
DB_SETTINGS = get_db_settings()
class Database:
    
    @staticmethod
    def DB() -> DatabaseABC:
        
        if DB_SETTINGS.db_handler == "neo4j":
            from lib.database.neo4j.Database import DB
    
        # elif DB_SETTINGS.db_handler == "postgresql":
        #     from lib.database.ProstgreSQLDatabase import DB
    
        
        return DB 