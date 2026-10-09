import logging
from datetime import timedelta

from lib.cache.cache import db_cache_runtime

logger = logging.getLogger(__name__)

# Short TTL: bounds the staleness of the submission scope if an invalidation
# hook is ever missed, while keeping group memberships / share approvals
# effective almost immediately through the explicit invalidation hooks.
SCOPE_CACHE_TTL = timedelta(seconds=60)
SCOPE_CACHE_NAMESPACE = "submission_scope"


def make_scope_cache_key(user_tag: str) -> str:
    return db_cache_runtime.make_cache_key(key_data={"user_tag": user_tag}, namespace=SCOPE_CACHE_NAMESPACE)


def get_cached_scope(user_tag: str) -> "list[str] | None":
    """Returns the cached submission scope for the tag or None on a cache miss.
    Only actual scopes are cached (never the None/unrestricted curator case,
    which is derived from the role on each request via the user cache).
    Cache errors degrade to a miss, so a cache outage never breaks the API."""
    try:
        data = db_cache_runtime.get(make_scope_cache_key(user_tag))
    except Exception as e:
        logger.warning("Scope cache read failed for tag %s, treating as miss: %s", user_tag, e)
        return None
    if data is None:
        return None
    try:
        return list(data)
    except Exception as e:
        logger.warning("Dropping invalid cached scope entry for tag %s: %s", user_tag, e)
        invalidate_cached_scope(user_tag)
        return None


def cache_scope(user_tag: str, scope_tags: "list[str]", cache_time: timedelta = SCOPE_CACHE_TTL) -> None:
    try:
        db_cache_runtime.set(make_scope_cache_key(user_tag), list(scope_tags), cache_time)
    except Exception as e:
        logger.warning("Scope cache write failed for tag %s: %s", user_tag, e)


def invalidate_cached_scope(user_tag: str) -> None:
    try:
        db_cache_runtime.invalidate(make_scope_cache_key(user_tag))
    except Exception as e:
        logger.warning("Scope cache invalidation failed for tag %s: %s", user_tag, e)


def invalidate_all_cached_scopes() -> int:
    """Bulk invalidation, e.g. after writes that affect the scope of many users
    at once (consortium membership changes)."""
    return db_cache_runtime.invalidate_namespace(SCOPE_CACHE_NAMESPACE)
