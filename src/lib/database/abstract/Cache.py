import hashlib
from abc import ABC, abstractmethod
from typing import List 
class CacheABC(ABC):
    def __init__(self, max_items: int = 200):
        self.max_items = max_items
        self._cache = {}
        
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        """
        return key in self._cache

    def get(self, key: str):
        """
        Retrieve a value from the cache by key. Returns None if the key is not found.
        """
        return self._cache.get(key, None)

    def insert(self, key: str, value):
        """
        Insert a value into the cache. If the cache exceeds max_items, remove the oldest item.
        """
        if key not in self._cache and len(self._cache) >= self.max_items:
            # Remove the oldest item (FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value

    @staticmethod
    def calculate_key(settings: List[str]) -> str:
        """
        Calculate a cache key based on a list of settings (strings).
        The key is a SHA256 hash of the joined settings.
        """
        joined = '|'.join(settings)
        return hashlib.sha256(joined.encode('utf-8')).hexdigest()
