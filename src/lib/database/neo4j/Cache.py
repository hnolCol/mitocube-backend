
from lib.database.abstract.Cache import CacheABC

class Neo4JCache(CacheABC):
    def __init__(self):
        self.cache = {}
        
        
        