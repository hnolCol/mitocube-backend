import logging

from contextlib import asynccontextmanager
from lib.ai.agent.runtime import ai_agent_runtime
from lib.mfa.mfa import mfa_runtime
from lib.cache.cache import db_cache_runtime
from lib.database.Database import Database

logger = logging.getLogger(__name__)


async def _safe_startup(name: str, startup_coro, health_check=None) -> None:
    """Start a runtime; log and continue on failure.

    A failing dependency (Neo4j, MongoDB) is logged loudly but never aborts
    the app process, so a transient outage does not put the service down.
    Requests touching the affected dependency will error until it recovers.
    """
    try:
        if startup_coro is not None:
            await startup_coro()
        if health_check is not None:
            health_check()
        logger.info(f"{name} startup successful.")
    except Exception:
        logger.exception(f"{name} startup FAILED (health check or initialization). Continuing anyway.")


@asynccontextmanager
async def lifespan(app):
    await _safe_startup("Database (Neo4j)", None, Database.DB().health_check)
    await _safe_startup("AI agent runtime", ai_agent_runtime.startup, ai_agent_runtime.health_check)
    await _safe_startup("MFA runtime", mfa_runtime.startup, mfa_runtime.health_check)
    await _safe_startup("DB cache runtime", db_cache_runtime.startup, db_cache_runtime.health_check)
    try:
        yield
    finally:
        await ai_agent_runtime.shutdown()
        await mfa_runtime.shutdown()
        await db_cache_runtime.shutdown()
