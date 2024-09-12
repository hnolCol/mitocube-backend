



from config.settings.db import get_db_settings
from lib.data.database.ABCDatabase import DatabaseABC

DB_SETTINGS = get_db_settings()
print(DB_SETTINGS.db_handler)
class Database:
    
    @staticmethod
    def DB() -> DatabaseABC:
        
        if DB_SETTINGS.db_handler == "neo4j":
            from lib.data.database.neo4j.Database import DB
    
        elif DB_SETTINGS.db_handler == "postgresql":
            from lib.data.database.ProstgreSQLDatabase import DB
      
        elif DB_SETTINGS.db_handler == 'pandafiles':
            from lib.data.database.FileDatabase import DB        
        
        return DB 