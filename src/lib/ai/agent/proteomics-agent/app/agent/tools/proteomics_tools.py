"""
LangChain tool definitions wrapping the existing `DB.*` interfaces.

DESIGN NOTES (read this before adding a new tool):

1. Each tool wraps exactly one DB interface call. Don't make "do everything"
   tools — the agent composes simple tools far more reliably than it uses one
   complicated one.

2. The docstring/description is the ONLY thing the model sees to decide
   whether and how to call this tool. Write it like documentation for a new
   colleague who knows proteomics but has never seen your schema:
     - what it returns (shape, not just a noun)
     - what each parameter actually matches against
     - edge cases (empty results, case sensitivity, etc.)
     - when to prefer this tool over a similarly-named one

3. Keep return values small and structured. If a query can return thousands
   of rows (common in proteomics — e.g. peptide-level data), summarize or
   truncate in the tool itself rather than dumping everything into the
   model's context. The model can always ask a follow-up tool for more detail.

4. These tools are READ-ONLY by construction. If you need write tools later
   (e.g. annotate_submission), put them in a separate module and gate them
   behind explicit confirmation in the agent layer — don't mix them in here.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Replace this with however you actually import your DB layer.
# e.g. from app.db import DB
from app.services.db import DB


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

class FindSubmissionsInput(BaseModel):
    search_string: str = Field(
        default="",
        description=(
            "Free-text search matched against submission title, PI name, and "
            "organism. Leave empty to list all submissions (results are capped "
            "at 25 — ask the user to narrow the search if they need more)."
        ),
    )
class FindSubmissionsInput(BaseModel):
    search_string: str = Field(
        default="",
        description=(
            "Free-text search matched against submission title, PI name, and "
            "organism. Leave empty to list all submissions (results are capped "
            "at 25 — ask the user to narrow the search if they need more)."
        ),
    )
    user_tag: str | None = Field(
        default=None,
        description="Required user tag to filter submissions by current user. The user tag is important to set the scope of the user (e.g. what is the user allowed to access.)",
    )

@tool("find_submissions", args_schema=FindSubmissionsInput)
def find_submissions(user_tag : str, search_string: str = "") -> str:
    """Search proteomics submissions by title, PI name, or organism.

    Returns a JSON list of matching submissions, each with:
    submission_id, title, pi_name, organism, date_submitted, n_samples.

    Use this FIRST when the user refers to a study by name, topic, PI, or
    organism but you don't yet have a submission_id. Once you have a
    submission_id from this tool's output, use get_submission_details or
    find_proteins_by_submission rather than searching again.

    Returns an empty list (not an error) if nothing matches.
    """
    results = DB.submission_filter.find(current_user = user_tag, search_string=search_string)
    truncated = results[:25]
    return json.dumps(
        {
            "count_returned": len(truncated),
            "count_total": len(results),
            "submissions": truncated,
        },
        default=str,
    )


class GetSubmissionDetailsInput(BaseModel):
    submission_id: str = Field(
        ...,
        description="Exact submission ID, as returned by find_submissions.",
    )


@tool("get_submission_details", args_schema=GetSubmissionDetailsInput)
def get_submission_details(submission_id: str) -> str:
    """Get full metadata for one known submission.

    Returns a JSON object with submission_id, title, abstract, pi_name,
    organism, instrument, sample_count, and processing_status.

    Use this when you already have a submission_id (e.g. from
    find_submissions) and need more detail than the search result gave you.
    Do NOT use this to search by name — use find_submissions for that.

    Returns {"error": "not_found"} if the ID does not exist; do not retry
    with a guessed ID, ask the user to confirm it instead.
    """
    result = DB.submissions.get(submission_id=submission_id)
    if result is None:
        return json.dumps({"error": "not_found", "submission_id": submission_id})
    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Proteins
# ---------------------------------------------------------------------------

class FindProteinsBySubmissionInput(BaseModel):
    submission_id: str = Field(
        ..., description="Submission ID to list identified proteins for."
    )
    min_abundance: float | None = Field(
        default=None,
        description=(
            "Optional lower bound filter on abundance/intensity. Omit to "
            "return all identified proteins regardless of abundance."
        ),
    )
    limit: int = Field(
        default=50,
        description="Max rows to return. Increase only if the user explicitly asks for more.",
    )


@tool("find_proteins_by_submission", args_schema=FindProteinsBySubmissionInput)
def find_proteins_by_submission(
    submission_id: str,
    min_abundance: float | None = None,
    limit: int = 50,
) -> str:
    """List proteins identified in a given submission.

    Returns a JSON list of proteins with: protein_id, gene_name, accession,
    abundance, n_peptides, coverage_pct. Sorted by abundance descending.

    Requires a submission_id — get one first via find_submissions if the
    user only gave you a study name. This can return large result sets for
    deep proteomics runs; the `limit` and `min_abundance` parameters exist to
    keep responses manageable, prefer narrowing over raising limit blindly.
    """
    results = DB.proteins.find_by_submission(
        submission_id=submission_id,
        min_abundance=min_abundance,
        limit=limit,
    )
    return json.dumps({"count": len(results), "proteins": results}, default=str)


class CompareProteinAcrossSubmissionsInput(BaseModel):
    gene_name: str = Field(
        ..., description="Gene name or protein accession to compare, e.g. 'TP53' or 'P04637'."
    )
    submission_ids: list[str] = Field(
        ...,
        description="Two or more submission IDs to compare abundance of this protein across.",
    )


@tool(
    "compare_protein_across_submissions",
    args_schema=CompareProteinAcrossSubmissionsInput,
)
def compare_protein_across_submissions(
    gene_name: str, submission_ids: list[str]
) -> str:
    """Compare one protein's abundance across multiple submissions.

    Returns a JSON list with one entry per submission_id containing:
    submission_id, found (bool), abundance (or null if not detected).

    Use this for "how does X compare between study A and study B" style
    questions, instead of calling find_proteins_by_submission once per
    submission and comparing manually — this tool does the alignment for you
    and correctly reports proteins that were not detected in a given run.
    """
    results = DB.proteins.compare_across_submissions(
        gene_name=gene_name, submission_ids=submission_ids
    )
    return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# Tool registry — import this list in the agent
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    find_submissions,
    get_submission_details,
    find_proteins_by_submission,
    compare_protein_across_submissions,
]
