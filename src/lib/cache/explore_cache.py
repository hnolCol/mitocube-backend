import logging
from datetime import timedelta
from typing import List, Optional

from lib.cache.cache import db_cache_runtime
from config.models.collaborations import (
    SubmissionExploreConditionApplicationItemModel,
    SubmissionExploreConditionApplicationModel,
)

logger = logging.getLogger(__name__)

# Short TTL: bounds the staleness of the explore condition application aggregate
# (e.g. newly created submissions appear within two minutes) while taking the
# aggregation load off neo4j on every explore view. The aggregate is not
# user-specific (explore visibility depends only on the submission owner's
# research group, never on the requesting user), so one shared entry per limit
# is sufficient and no per-user keys are needed.
EXPLORE_CA_CACHE_TTL = timedelta(seconds=120)
EXPLORE_CA_CACHE_NAMESPACE = "explore_condition_applications"


def make_explore_ca_cache_key(limit: int) -> str:
    return db_cache_runtime.make_cache_key({"limit": limit}, namespace=EXPLORE_CA_CACHE_NAMESPACE)


def _serialize(models: List[SubmissionExploreConditionApplicationModel]) -> List[dict]:
    return [model.model_dump() for model in models]


def _deserialize(data) -> Optional[List[SubmissionExploreConditionApplicationModel]]:
    if not isinstance(data, list):
        return None
    try:
        return [
            SubmissionExploreConditionApplicationModel(
                submission_tag=entry["submission_tag"],
                condition_applications=[
                    SubmissionExploreConditionApplicationItemModel(**ca) for ca in entry.get("condition_applications", [])
                ]
            )
            for entry in data
        ]
    except Exception as e:
        logger.warning("Dropping invalid cached explore condition application entry: %s", e)
        return None


def get_cached_explore_cas(limit: int) -> Optional[List[SubmissionExploreConditionApplicationModel]]:
    """Returns the cached explore condition application aggregate for the
    limit or None on a cache miss. Cache errors degrade to a miss, so a cache
    outage never breaks the API."""
    try:
        data = db_cache_runtime.get(make_explore_ca_cache_key(limit))
    except Exception as e:
        logger.warning("Explore condition application cache read failed, treating as miss: %s", e)
        return None
    if data is None:
        return None
    return _deserialize(data)


def cache_explore_cas(models: List[SubmissionExploreConditionApplicationModel], limit: int,
                      cache_time: timedelta = EXPLORE_CA_CACHE_TTL) -> None:
    try:
        db_cache_runtime.set(make_explore_ca_cache_key(limit), _serialize(models), cache_time)
    except Exception as e:
        logger.warning("Explore condition application cache write failed: %s", e)


def invalidate_cached_explore_cas() -> int:
    """Bulk invalidation of all explore condition application cache entries."""
    return db_cache_runtime.invalidate_namespace(EXPLORE_CA_CACHE_NAMESPACE)
