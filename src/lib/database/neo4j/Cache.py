
from lib.database.abstract.Cache import CacheABC

class Neo4JCache(CacheABC):
    def __init__(self, max_items: int = 200):
        super().__init__(max_items=max_items)
        