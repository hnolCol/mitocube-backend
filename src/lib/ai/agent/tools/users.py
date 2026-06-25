from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from lib.database.Database import Database

DB = Database.DB()


# ============================================================
# Input Schemas
# ============================================================

class UserTagInput(BaseModel):
    user_tag: str = Field(
        ...,
        description="The user tag identifying a specific user."
    )


class UserSearchInput(BaseModel):
    search_string: Optional[str] = Field(
        None,
        description="Search text used to find users by name or other user information."
    )

    limit: int = Field(
        20,
        description="Maximum number of user tags to return."
    )


# ============================================================
# User Search
# ============================================================

@tool("find_users", args_schema=UserSearchInput)
def find_users(
    search_string: str = None,
    limit: int = 20
) -> List[str]:
    """
    Search users by name or free text search.

    Returns matching user tags.

    Use this tool when the user refers to a person by name and the exact
    user tag is not known.
    """

    return DB.users.find(
        search_string=search_string,
        limit=limit
    )


# ============================================================
# User Summary
# ============================================================

@tool("get_user_summary", args_schema=UserTagInput)
def get_user_summary(user_tag: str):
    """
    Retrieve a concise summary of a user.

    This is the preferred tool whenever information about a user is requested.
    It combines profile information, activity status and submission statistics
    into a single response.
    """

    user = DB.users.get_user_by_tag(user_tag)

    if user is None:
        return None

    try:
        submission_count = len(
            DB.submission_filter.filter_by_user(
                user_tags=[user_tag]
            )
        )
    except Exception:
        submission_count = 0 
        
    favorite_proteins = DB.proteins.get_favorite_proteins(user_tag=user_tag)
    print("get_user_summary called with user_tag:", user_tag, "submission_count:", submission_count)
    
    return {
        "user_tag": user_tag,
        "firstname": getattr(user, "firstname", None),
        "lastname": getattr(user, "lastname", None),
        "email": getattr(user, "email", None),
        "institution": getattr(user, "institution", None),
        "research_group": getattr(user, "research_group", None),
        "role": getattr(user, "role", None),
        "active": DB.users.is_user_active(tag=user_tag),
        "submission_count": submission_count,
        "favorite_proteins": favorite_proteins
    }


# ============================================================
# User Details
# ============================================================

@tool("get_user_details", args_schema=UserTagInput)
def get_user_details(user_tag: str):
    """
    Retrieve the complete public user object.

    Use this tool only when detailed information beyond the user summary
    is required.
    """

    return DB.users.get_user_by_tag(user_tag)


# ============================================================
# User Status
# ============================================================

@tool("check_user_exists", args_schema=UserTagInput)
def check_user_exists(user_tag: str) -> bool:
    """
    Check whether a user exists.
    """

    return DB.users.exists(tag=user_tag)


@tool("count_user_submissions", args_schema=UserTagInput)
def count_user_submissions(user_tag: str) -> int:
    """
    Count the number of submissions associated with a user.
    """

    if not DB.users.exists(tag=user_tag):
        return 0

    return len(
        DB.submission_filter.filter_by_user(
            user_tags=[user_tag]
        )
    )


# ============================================================
# Registry
# ============================================================

USER_TOOLS = [
    find_users,
    get_user_summary,
    get_user_details,
    check_user_exists,
    count_user_submissions,
]