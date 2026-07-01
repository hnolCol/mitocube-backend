"""
Holds the agent + checkpointer for the lifetime of the FastAPI app.

Why this exists: AsyncSqliteSaver wraps a single aiosqlite connection. You
want exactly one of these per process, created at startup and closed at
shutdown — not one per request. FastAPI's lifespan context is the right
place for that; see app/main.py.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from langgraph.checkpoint.mongodb import MongoDBSaver

from lib.ai.agent.agent import build_agent
from lib.ai.agent.config import get_mongo_ai_db_settings
settings = get_mongo_ai_db_settings()
class AgentRuntime:
    def __init__(self) -> None:
        self.agent = None
        self._checkpointer_cm = None

    async def startup(self) -> None:
        self._checkpointer_cm = MongoDBSaver.from_conn_string(
            settings.AGENT_MONGO_URI, 
            settings.AGENT_MONGO_DB_NAME,
        )
        # Sync __enter__/__exit__ — this is intentional, see module docstring.
        checkpointer = self._checkpointer_cm.__enter__()
        self.agent = build_agent(checkpointer=checkpointer)

    async def shutdown(self) -> None:
        if self._checkpointer_cm is not None:
            self._checkpointer_cm.__exit__(None, None, None)


runtime = AgentRuntime()


@asynccontextmanager
async def lifespan(app):
    await runtime.startup()
    try:
        yield
    finally:
        await runtime.shutdown()
