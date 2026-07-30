# services/neo4j_cache/runtime.py
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

from pymongo import MongoClient
from lib.ai.agent.config import get_mongo_db_settings

mongo_db_settings = get_mongo_db_settings()
logger = logging.getLogger(__name__)

# Mongo's hard per-document limit. Writing above this will fail outright.
MAX_DOCUMENT_SIZE_BYTES = 16 * 1024 * 1024

# Soft threshold: entries above this still get cached, but we log a warning.
# Large entries cost more on every read/write and creep toward the hard limit.
DEFAULT_WARN_SIZE_BYTES = 1 * 1024 * 1024


class DBCacheRuntime:
    """
    Generic result-cache for expensive Neo4j reads, backed by Mongo with a
    TTL index (same expiry mechanism as MFARuntime). Each entry gets its own
    `cache_time`, so cheap/volatile queries and expensive/stable queries can
    live side by side with different lifetimes.
    """

    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.cache = None

    async def startup(self) -> None:
        self.client = MongoClient(mongo_db_settings.AGENT_MONGO_URI)
        db = self.client[mongo_db_settings.MFA_MONGO_DB_NAME]  # swap for a dedicated cache DB name

        self.cache = db["neo4j_query_cache"]
        self.cache.create_index("expires_at", expireAfterSeconds=0)
        self.cache.create_index("cache_key", unique=True)

    async def shutdown(self) -> None:
        if self.client is not None:
            self.client.close()

    # --- key building ---
    @staticmethod
    def make_cache_key(key_data: Any, namespace: str = "default") -> str:
        """
        Deterministic key from arbitrary key material. `key_data` can be a
        query string, a dict of {query, params}, a tuple of args, a plain
        identifier - anything JSON-serializable (falls back to str() for
        anything that isn't, e.g. datetimes, sets, custom objects).

        Always include a namespace that encodes anything the result depends
        on beyond key_data itself (e.g. tenant_id, user_id, schema_version)
        so entries never leak across contexts and a schema bump auto-
        invalidates old entries.
        """
        payload = json.dumps(key_data, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"{namespace}:{digest}"

    # --- serialization: Mongo/BSON only understands JSON-native types
    # (dict, list, str, int, float, bool, None, datetime). Anything else -
    # DataFrames, numpy scalars, custom class instances - needs converting
    # first. We auto-handle pandas since it's a common case; anything else
    # unencodable is caught in `set()` with an actionable error message.
    @staticmethod
    def _serialize(data: Any) -> Any:
        try:
            import pandas as pd
        except ImportError:
            pd = None

        if pd is not None and isinstance(data, pd.DataFrame):
            parsed = json.loads(data.to_json(orient="split", date_format="iso"))
            return {
                "__cache_type__": "pandas.DataFrame",
                "index": parsed["index"],
                "columns": parsed["columns"],
                "data": parsed["data"],
            }

        if pd is not None and isinstance(data, pd.Series):
            parsed = json.loads(data.to_json(orient="split", date_format="iso"))
            return {
                "__cache_type__": "pandas.Series",
                "index": parsed["index"],
                "data": parsed["data"],
                "name": data.name,
            }

        return data

    @staticmethod
    def _deserialize(stored: Any) -> Any:
        if isinstance(stored, dict) and "__cache_type__" in stored:
            import pandas as pd  # only reached if we serialized pandas data in the first place

            if stored["__cache_type__"] == "pandas.DataFrame":
                return pd.DataFrame(data=stored["data"], index=stored["index"], columns=stored["columns"])
            if stored["__cache_type__"] == "pandas.Series":
                return pd.Series(data=stored["data"], index=stored["index"], name=stored["name"])

        return stored

    # --- core cache ops ---
    @staticmethod
    def _estimate_size_bytes(cache_key: str, data: Any) -> int:
        """
        Best-effort size of what will actually be stored, based on a JSON
        encoding of the document. This slightly undercounts the true BSON
        size (BSON adds a small amount of per-field type/length overhead),
        but it's close enough to be useful as a warning threshold without
        depending on pymongo's internal bson encoder.
        """
        probe = {"cache_key": cache_key, "data": data}
        return len(json.dumps(probe, default=str).encode("utf-8"))

    def set(
        self,
        cache_key: str,
        data: Any,
        cache_time: timedelta,
        warn_size_bytes: int = DEFAULT_WARN_SIZE_BYTES,
    ) -> bool:
        """
        Returns True if the entry was cached, False if it was rejected for
        being too large or for containing a type Mongo can't encode. Logs a
        warning above `warn_size_bytes` and refuses outright above Mongo's
        16MB hard document limit (rather than letting the driver throw on
        find_one_and_update).
        """
        data = self._serialize(data)
        size = self._estimate_size_bytes(cache_key, data)

        if size > MAX_DOCUMENT_SIZE_BYTES:
            logger.error(
                "Refusing to cache '%s': entry is %.2fMB, exceeds Mongo's "
                "16MB document limit. Consider summarizing/trimming the "
                "result before caching, or storing it elsewhere (e.g. GridFS).",
                cache_key, size / (1024 * 1024),
            )
            return False

        if size > warn_size_bytes:
            logger.warning(
                "Cache entry '%s' is %.2fMB (> %.2fMB warn threshold). "
                "Large entries increase read/write cost and creep toward "
                "Mongo's 16MB document limit - consider a shorter cache_time "
                "or trimming the payload.",
                cache_key, size / (1024 * 1024), warn_size_bytes / (1024 * 1024),
            )

        now = datetime.now(timezone.utc)
        try:
            self.cache.find_one_and_update(
                {"cache_key": cache_key},
                {
                    "$set": {
                        "data": data,
                        "created_at": now,
                        "expires_at": now + cache_time,
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(
                "Failed to write cache entry '%s': %s. Mongo can only store "
                "JSON-native types (dict, list, str, int, float, bool, None, "
                "datetime). If `data` contains something else (a custom "
                "class instance, numpy scalar, etc.) convert it to a plain "
                "structure first - pandas DataFrame/Series are handled "
                "automatically.",
                cache_key, e,
            )
            return False
        return True

    def get(self, cache_key: str) -> Any | None:
        doc = self.cache.find_one({"cache_key": cache_key})
        if not doc:
            return None
        return self._deserialize(doc["data"])

    def invalidate(self, cache_key: str) -> None:
        self.cache.delete_one({"cache_key": cache_key})

    def invalidate_namespace(self, namespace: str) -> int:
        """Bulk-invalidate everything under a namespace, e.g. after a write
        that affects a known set of cached reads (user's graph, a org's tree, etc.)."""
        result = self.cache.delete_many({"cache_key": {"$regex": f"^{namespace}:"}})
        return result.deleted_count

    # --- convenience wrappers ---
    def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable[[], Any],
        cache_time: timedelta,
        warn_size_bytes: int = DEFAULT_WARN_SIZE_BYTES,
    ) -> Any:
        cached = self.get(cache_key)
        if cached is not None:
            return cached
        result = compute_fn()
        # If the result is too large to cache, we still return it to the
        # caller - caching is a performance optimization, not a correctness
        # requirement, so a rejected write shouldn't break the caller.
        self.set(cache_key, result, cache_time, warn_size_bytes=warn_size_bytes)
        return result

    async def async_get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable[[], Awaitable[Any]],
        cache_time: timedelta,
        warn_size_bytes: int = DEFAULT_WARN_SIZE_BYTES,
    ) -> Any:
        """Same as get_or_compute, for the (typical) async Neo4j driver."""
        cached = self.get(cache_key)
        if cached is not None:
            return cached
        result = await compute_fn()
        self.set(cache_key, result, cache_time, warn_size_bytes=warn_size_bytes)
        return result


db_cache_runtime = DBCacheRuntime()