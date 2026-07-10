
from contextlib import asynccontextmanager
from lib.ai.agent.runtime import ai_agent_runtime
from lib.mfa.mfa import mfa_runtime

@asynccontextmanager
async def lifespan(app):
    await ai_agent_runtime.startup()
    await mfa_runtime.startup()
    try:
        yield
    finally:
        await ai_agent_runtime.shutdown()
        await mfa_runtime.shutdown()
