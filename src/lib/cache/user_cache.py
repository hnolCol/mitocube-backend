import logging
from datetime import timedelta

from lib.cache.cache import db_cache_runtime
from config.models.user import UserModel

logger = logging.getLogger(__name__)

# Short TTL: cuts the per-request Neo4j user lookup while keeping role
# revocations and login blocks effective almost immediately.
USER_CACHE_TTL = timedelta(seconds=30)
USER_CACHE_NAMESPACE = "user"


def make_user_cache_key(user_tag: str) -> str:
    return db_cache_runtime.make_cache_key(key_data={"user_tag": user_tag}, namespace=USER_CACHE_NAMESPACE)


def get_cached_user(user_tag: str) -> UserModel | None:
    """Returns the cached UserModel for the tag or None on a cache miss.
    The cached payload never contains secrets (password, mfa_secret)."""
    data = db_cache_runtime.get(make_user_cache_key(user_tag))
    if data is None:
        return None
    try:
        return UserModel(**data)
    except Exception as e:
        logger.warning("Dropping invalid cached user entry for tag %s: %s", user_tag, e)
        invalidate_cached_user(user_tag)
        return None


def cache_user(user: UserModel, cache_time: timedelta = USER_CACHE_TTL) -> None:
    """Caches a user with secrets (password, mfa_secret) excluded. None values are
    omitted so the UserModel can be reconstructed from its defaults."""
    payload = user.model_dump(exclude={"password", "mfa_secret"}, exclude_none=True)
    db_cache_runtime.set(make_user_cache_key(user.tag), payload, cache_time)


def invalidate_cached_user(user_tag: str) -> None:
    db_cache_runtime.invalidate(make_user_cache_key(user_tag))


def invalidate_all_cached_users() -> int:
    return db_cache_runtime.invalidate_namespace(USER_CACHE_NAMESPACE)
