import logging

from contextlib import asynccontextmanager
from lib.ai.agent.runtime import ai_agent_runtime
from lib.mfa.mfa import mfa_runtime
from lib.cache.cache import db_cache_runtime
from lib.database.Database import Database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    try:
        Database.DB().health_check()
        logger.info("Database health check passed.")
    except Exception:
        logger.exception("Database health check FAILED at startup.")
    await ai_agent_runtime.startup()
    await mfa_runtime.startup()
    await db_cache_runtime.startup()
    try:
        yield
    finally:
        await ai_agent_runtime.shutdown()
        await mfa_runtime.shutdown()
        await db_cache_runtime.shutdown()
