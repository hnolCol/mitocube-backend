"""Central settings, env-driven so you don't hardcode model choice or paths."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Provider-prefixed model string. Swap providers by changing this alone.
    # Examples: "anthropic:claude-sonnet-4-6", "openai:gpt-4.1"

    AGENT_MONGO_URI: str = os.environ.get("AGENT_MONGO_URI", "mongodb://localhost:27017")
    AGENT_MONGO_DB_NAME: str = os.environ.get("AGENT_MONGO_DB_NAME", "agent_sessions")

settings = Settings()
