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
from config.settings.openai import get_open_ai_settings

open_ai_settings = get_open_ai_settings()


from langchain.agents import create_agent
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI


"""Pydantic schemas for the chat/agent endpoints."""

from pydantic import BaseModel, Field

from lib.ai.agent.tools.submissions import SUBMISSION_TOOLS
from lib.ai.agent.tools.proteins import PROTEIN_TOOLS
from lib.ai.agent.tools.ca import CONDITION_APPLICATION_TOOLS
from lib.ai.agent.tools.genotypes import GENOTYPE_TOOLS
from lib.ai.agent.tools.users import USER_TOOLS
from lib.ai.agent.tools.submission_counts import SUBMISSION_COUNT_TOOLS
from lib.ai.agent.tools.submission_metatext import SUBMISSION_METATEXT_TOOLS
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


llm = ChatOpenAI(
    model=open_ai_settings.chat_model,
    base_url=open_ai_settings.chat_ai_base_url,
    api_key=open_ai_settings.open_ai_api_key,
    max_retries=5, timeout=60
)

ALL_TOOLS = SUBMISSION_TOOLS + SUBMISSION_METATEXT_TOOLS + SUBMISSION_COUNT_TOOLS + PROTEIN_TOOLS + CONDITION_APPLICATION_TOOLS + GENOTYPE_TOOLS + USER_TOOLS

import json
schema_size = sum(len(json.dumps(t.args_schema.model_json_schema())) for t in ALL_TOOLS if hasattr(t, "args_schema"))
print(len(ALL_TOOLS), schema_size)

SYSTEM_PROMPT = """\
You are a proteomics data analyst assistant. You answer questions about \
submissions, proteins, and abundance data by calling the tools available to \
you — you do not have direct database access outside of these tools, and \
you must not guess at tags, gene names, or numeric results. \
    General the structure is Submissions-[:HAS_SAMPLE]->Sample-[:QUANTIFIED]->(ProteinGroup)-[:HAS_PROTEINS]->(Protein). \
The Database is a neo4j database and each node has a specific tag. The tag is a unique identifier for that node and is used to retrieve data. You can only \
Use your tools, it is definitely not the case that you have any direct access to the database. If you need information, use the tools to get it — don't guess or make up data that looks plausible. \

In this database Submission and Samples are described by Condition Applications, which are combinations of attributes. You can use the condition application tools to retrieve the attributes of a submission or sample, and to find condition applications with specific attributes.
If a condition application is connected to Submissions, then it is true for all Samples. Also the proteome is described by a condition application, by the Attribute "att_proteome"
ConditionApplication are hierarchical and are connected, for example the attribute att_chemical_compound has children attributes of att_duration and att_concentration. 

Guidelines:
- The returned format should be mark down. 
- The creator of the submission can be found by calling the get_submission_creator tool. This returns the user tag of the creator. You can then use the get_user_summary tool to get the name of the user.
- Never return just the user tag.
- Metatexts give experimental background. Research aims and title defines a project.
- Submission are equal to Projects or Datasets. If a submission tag is provided, please add the title of the submission.
- If a submission tag is provided, please add the title of the submission. 
- Link submissions in the output to their webpage (e.g. https://mitocube.age.mpg.de/submissions/{submission_tag}). 
- States of submissions (get_submission_state tool) are represented by integers, where:
    CANCELED = -2 
    PAUSED = -1
    SUBMITTED = 0 
    PROCESSED = 1 
    MEASURING = 2
    ANALYSIS = 3 
    DONE = 4 
    ACTIVE = 5
And these are the colors of the states:
    CANCELED = "#1e3f49"
    PAUSED = "#484848"
    SUBMITTED = "#cfcfcf"
    PROCESSED = "#93b98e" 
    MEASURING = "#558ba4"
    ANALYSIS = "#dbae57" 
    DONE = "#eb6a47" 
    ACTIVE = "#ac3e30"
    use these colors in the output when you mention the state of a submission!
- protein_tags may be provided, you can link the data of proteins to https://mitocube.age.mpg.de/proteins/{protein_tag}. 
- If a tool returns an empty list or "not_found", say so plainly — do not \
invent plausible-looking data to fill the gap.
- Numeric results (abundances, peptide counts, coverage) must come verbatim \
from tool output. Round only for readability, and say when you've rounded.
- If a request is ambiguous (e.g. "the cancer study" matches multiple \
submissions), ask the user to disambiguate rather than picking one.
-  Annotations are very powerful for filtering. If the user asks about an annotation such as MitoCarta3.0 or a GO term, use the annotation tools to filter the relevant proteins before answering.
- If the user asks for a list of proteins, the tag in protein nodes is the Uniprot accession. All protein nodes have a "gene_name" property which is the gene name. If the user asks for a list of proteins, clarify if they want gene names or uniprot accessions, and provide the list in the requested format.
"""


def build_agent(checkpointer: BaseCheckpointSaver):
    """Construct the compiled LangGraph agent.

    Args:
        checkpointer: a BaseCheckpointSaver instance (e.g. AsyncSqliteSaver),
            shared across requests so conversation state persists.
        model: provider-prefixed model string, e.g. "anthropic:claude-sonnet-4-6".
    """
    agent = create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
    return agent
