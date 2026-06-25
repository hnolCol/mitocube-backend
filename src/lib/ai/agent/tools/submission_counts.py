from typing import Dict, List, Optional
 
from langchain_core.tools import tool
from pydantic import BaseModel, Field
 
from lib.database.Database import Database
from config.enums.states import SubmissionStatesEnums  # adjust import path to match your project
 
DB = Database.DB()
 
 
# ============================================================
# Input Schemas
# ============================================================
 
class SubmissionStateInput(BaseModel):
    state_tag: SubmissionStatesEnums = Field(
        ...,
        description="The submission state to count, e.g. 'pending', 'completed', 'failed'."
    )
 
 
class SubmissionTagInput(BaseModel):
    submission_tag: str = Field(
        ...,
        description="The submission tag identifying a specific submission."
    )
 
 
# ============================================================
# Submission State Count
# ============================================================
 
@tool("get_submission_state_count", args_schema=SubmissionStateInput)
def get_submission_state_count(state_tag: SubmissionStatesEnums) -> int:
    """
    Return the number of submissions currently in a given state.
 
    Use this tool when the user asks how many submissions are pending,
    completed, failed, or in any other specific state. This is a global
    count across all submissions, not scoped to a single submission.
    """
 
    if not DB.submissions.exists(state=state_tag):
        return 0
 
    return DB.submissions.count(state=state_tag)
 
 
# ============================================================
# Lightweight per-submission counts
# ============================================================
 
@tool("get_submission_protein_group_count", args_schema=SubmissionTagInput)
def get_submission_protein_group_count(submission_tag: str) -> int:
    """
    Return the number of protein groups for a given submission.
 
    Use this tool when the user asks specifically about protein group
    counts for one submission and does not need the full overview
    (peptides, samples, etc). For a complete picture of a submission,
    prefer get_submission_overview instead.
    """
 
    if not DB.submissions.exists(tag=submission_tag):
        raise ValueError(f"Submission '{submission_tag}' not found.")
 
    return DB.protein_groups.count(submission_tag=submission_tag)
 
 
@tool("get_submission_peptide_count", args_schema=SubmissionTagInput)
def get_submission_peptide_count(submission_tag: str) -> int:
    """
    Return the number of peptides for a given submission.
 
    Use this tool when the user asks specifically about peptide counts
    for one submission and does not need the full overview. For a
    complete picture of a submission, prefer get_submission_overview
    instead.
    """
 
    if not DB.submissions.exists(tag=submission_tag):
        raise ValueError(f"Submission '{submission_tag}' not found.")
 
    return DB.peptides.count(submission_tag=submission_tag)
 
 
@tool("get_submission_sample_count", args_schema=SubmissionTagInput)
def get_submission_sample_count(submission_tag: str) -> int:
    """
    Return the number of samples for a given submission.
 
    Use this tool when the user asks specifically about sample counts
    for one submission and does not need the full overview. For a
    complete picture of a submission, prefer get_submission_overview
    instead.
    """
 
    if not DB.submissions.exists(tag=submission_tag):
        raise ValueError(f"Submission '{submission_tag}' not found.")
 
    return DB.samples.count(submission_tag=submission_tag)
 
 
# ============================================================
# Composite overview
# ============================================================
 
@tool("get_submission_overview", args_schema=SubmissionTagInput)
def get_submission_overview(submission_tag: str) -> Dict:
    """
    Return a complete overview of a submission in a single call: protein
    group count, peptide count, sample count, and the quantified protein
    group count per sample.
 
    Use this tool whenever the user asks for a summary, overview, or
    general status of a submission, or asks about more than one of
    (protein groups, peptides, samples) at once. This avoids making
    several separate tool calls. Only use the single-metric tools
    (get_submission_protein_group_count, get_submission_peptide_count,
    get_submission_sample_count) when the user asks about exactly one
    of those metrics in isolation.
    """
 
    if not DB.submissions.exists(tag=submission_tag):
        raise ValueError(f"Submission '{submission_tag}' not found.")
 
    sample_tags = DB.submissions.get_samples(tag=submission_tag)
 
    samples = [
        {
            "tag": sample_tag,
            "quantified_protein_group_count": DB.samples.count_quantified_protein_groups(
                tag=sample_tag, submission_tag=submission_tag
            ),
        }
        for sample_tag in sample_tags
    ]
 
    return {
        "submission_tag": submission_tag,
        "protein_group_count": DB.protein_groups.count(submission_tag=submission_tag),
        "peptide_count": DB.peptides.count(submission_tag=submission_tag),
        "sample_count": DB.samples.count(submission_tag=submission_tag),
        "samples": samples,
    }


SUBMISSION_COUNT_TOOLS = [
    get_submission_protein_group_count,
    get_submission_peptide_count,
    get_submission_sample_count,
    get_submission_overview
]