"""Chat endpoint that routes user messages through the LangChain agent."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage

from app.agent.runtime import runtime
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if runtime.agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized yet.")

    config = {"configurable": {"thread_id": request.session_id}}

    result = await runtime.agent.ainvoke(
        {"messages": [{"role": "user", "content": request.message}]},
        config=config,
    )

    messages = result["messages"]
    last_ai_message = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)), None
    )
    reply = last_ai_message.content if last_ai_message else ""

    tool_calls = [
        call["name"]
        for m in messages
        if isinstance(m, AIMessage)
        for call in (m.tool_calls or [])
    ]

    return ChatResponse(session_id=request.session_id, reply=reply, tool_calls=tool_calls)
