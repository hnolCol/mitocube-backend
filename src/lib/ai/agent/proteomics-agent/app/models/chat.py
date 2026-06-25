"""Pydantic schemas for the chat/agent endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's natural-language question.")
    session_id: str = Field(
        ...,
        description=(
            "Stable identifier for this conversation. Generate one client-side "
            "(e.g. a UUID) the first time a user opens the analysis chat, and "
            "reuse it for every subsequent message in that conversation so the "
            "agent retains context."
        ),
    )


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    # Optional: surface which tools were called, useful for a "show your work"
    # UI panel in the frontend. Purely informational, safe to ignore.
    tool_calls: list[str] = Field(default_factory=list)
