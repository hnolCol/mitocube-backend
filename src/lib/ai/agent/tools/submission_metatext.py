from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from lib.database.Database import Database

DB = Database.DB()


# ============================================================
# Input Schemas
# ============================================================

class MetaTextExistsInput(BaseModel):
    tag: str = Field(
        ...,
        description="MetaText tag to check existence for."
    )


class MetaTextGetInput(BaseModel):
    tag: str = Field(
        ...,
        description="MetaText tag to retrieve."
    )


class MetaTextFindInput(BaseModel):
    submission_tag: Optional[str] = Field(
        None,
        description="Optional submission tag to filter MetaTexts."
    )


class MetaTextUpdateInput(BaseModel):
    tag: str = Field(
        ...,
        description="MetaText tag to update."
    )
    user_tag: str = Field(
        ...,
        description="User performing the update."
    )
    title: Optional[str] = Field(
        None,
        description="Optional new title for the MetaText."
    )
    text: Optional[str] = Field(
        None,
        description="Optional new text content for the MetaText."
    )


# ============================================================
# Tools
# ============================================================

@tool("metatext_exists", args_schema=MetaTextExistsInput)
def metatext_exists(tag: str) -> bool:
    """
    Check whether a MetaText exists in the database by tag.
    """
    return DB.meta_text.exists(tag=tag)


@tool("metatext_get", args_schema=MetaTextGetInput)
def metatext_get(tag: str):
    """
    Retrieve a MetaText by its tag.
    """
    return DB.meta_text.get(tag=tag)


@tool("metatext_find", args_schema=MetaTextFindInput)
def metatext_find(submission_tag: Optional[str] = None) -> List[str]:
    """
    Find MetaText tags.

    If submission_tag is provided, only MetaTexts linked to that submission are returned.
    Otherwise returns all MetaText tags ordered by creation time.
    """
    return DB.meta_text.find(submission_tag=submission_tag)



SUBMISSION_METATEXT_TOOLS = [
    metatext_exists,
    metatext_get,
    metatext_find
]