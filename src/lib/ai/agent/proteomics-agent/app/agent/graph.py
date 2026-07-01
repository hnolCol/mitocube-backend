"""
Builds the LangChain agent used for proteomics Q&A.

Provider is a config string, not code — see settings.AGENT_MODEL. Examples:
    "anthropic:claude-sonnet-4-6"
    "openai:gpt-4.1"
Swapping providers means changing one string (and having the right API key
in the environment); nothing else in this file needs to change.

Persistence: uses AsyncSqliteSaver (NOT the sync SqliteSaver) because FastAPI
is async and the sync saver does not handle concurrent threads safely. The
checkpointer is created once at app startup and reused for every request —
see app/agent/runtime.py for lifecycle wiring.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agent.tools.proteomics_tools import ALL_TOOLS

SYSTEM_PROMPT = """\
You are a proteomics data analyst assistant. You answer questions about \
submissions, proteins, and abundance data by calling the tools available to \
you — you do not have direct database access outside of these tools, and \
you must not guess at IDs, gene names, or numeric results.

Guidelines:
- If the user names a study, PI, or organism but you don't have a \
submission_id yet, call find_submissions first.
- If a tool returns an empty list or "not_found", say so plainly — do not \
invent plausible-looking data to fill the gap.
- When comparing across submissions, prefer compare_protein_across_submissions \
over manually combining two separate lookups.
- Numeric results (abundances, peptide counts, coverage) must come verbatim \
from tool output. Round only for readability, and say when you've rounded.
- If a request is ambiguous (e.g. "the cancer study" matches multiple \
submissions), ask the user to disambiguate rather than picking one.
"""


def build_agent(checkpointer: BaseCheckpointSaver, model: str):
    """Construct the compiled LangGraph agent.

    Args:
        checkpointer: a BaseCheckpointSaver instance (e.g. AsyncSqliteSaver),
            shared across requests so conversation state persists.
        model: provider-prefixed model string, e.g. "anthropic:claude-sonnet-4-6".
    """
    llm = init_chat_model(model)
    agent = create_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
    return agent
