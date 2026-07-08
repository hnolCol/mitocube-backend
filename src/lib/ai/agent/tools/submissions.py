
from typing import List, Optional, Dict, Tuple

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from lib.database.Database import Database 
from config.models.submissions.states import SubmissionStatesEnums
from config.models.parameter import APIParamString, APIParamInt
DB = Database.DB()

# =========================================================
# INPUT SCHEMAS
# =========================================================

class SubmissionQueryInput(BaseModel):
    search_string: Optional[str] = None
    state: Optional[List[SubmissionStatesEnums]] = None
    user_tags: Optional[List[str]] = None
    limit: int = 20

class SubmissionConditionApplicationInput(BaseModel):
    "Input model for ConditionApplications connected to a submission. This is used to filter the condition applications of a submission. This means that the condition application are true for all samples of the submission. The condition applications are hierarchical and can be grouped by attribute or by minimum state."
    submission_tag: str = Field(..., description="Exact submission tag to retrieve information for")
    group_by_min_state: bool = Field(False, description="Whether to group by minimum state. This is a property of an attribute. Some attribute can only be entered if a given state of submission is reached. For example: The instrument can only be defined, if the submission is in state 'Measuring'")
    group_by_attribute: bool = Field(True, description="Whether to group by attribute")
    attribute_tags : Optional[List[str]] = Field(None, description="List of attribute tags to filter by. This gives then only the condition applications that have the given attributes. If empty, all condition applications are returned.")
    

class FindSubmissionsInput(BaseModel):
    current_user_tag : str = Field(..., description="The user tag of the current user. This is used to filter the submissions that the user has access to.")
    search_string: str = Field("", description="Search string for submissions")
    state: List[SubmissionStatesEnums] = Field(None, description="Filter submissions by state (leave empty for all states)")
    user_tags: List[str] = Field(None, description="Filter submissions by user tag (leave empty for all users). You can user_tags by the find_users tool to find user tags based on names.")
    limit: int = Field(2, description="Maximum number of submission tags to return")
    ca_tags : List[str] = Field(None, description="Filter submissions by condition application tags (leave empty for all condition applications). You can use the find_condition_applications tool to find condition application tags based on names.")
    protein_tags: List[str] = Field(None, description="Filter submissions by protein tags (leave empty for all proteins). This will return only submission that quantified the given proteins.")
    
class SubmissionTagInput(BaseModel):
    submission_tag: str = Field(..., description="Exact submission tag to retrieve information for")
    
class SubmissionTagsInput(BaseModel):
    submission_tags: List[str] = Field(..., description="Exact submission tags to retrieve information for")
    
    
class SubmissionTitleAndAimOutput(BaseModel):
    submission_tag: str
    title: str
    research_aim: str
    
@tool("find_submissions", args_schema=FindSubmissionsInput)
def find_submissions(current_user_tag: str,
                     search_string: str = None, 
                     protein_tags: List[str] = None,
                     state: List[SubmissionStatesEnums] = None, 
                     user_tags: List[str] = None,
                     ca_tags : List[str] = None,
                     limit : int = 2) -> List[str]:
    """Search submissions by free text search on title, tags and research name.
    Returns a list of matching submission tags. The submission are automatically ordered by the creation_date
    - Comments: 
    
    If no search_string is provided and limit = 1, the most recent submission tag will be returned.
    
    """
    tags = DB.submission_filter.find(current_user_tag= current_user_tag, search_string=search_string, state=state, user_tags=user_tags, ca_tags=ca_tags, limit = limit, protein_tags=protein_tags)
    return tags

@tool("get_submission_title_and_research_aim", args_schema=SubmissionTagsInput)
def get_submission_title_and_research_aim(submission_tags: List[str]) -> List[SubmissionTitleAndAimOutput]:
    """Given a list of submission tags, return their titles and research aims."""
    results = []
    for tag in submission_tags:
        submission_title = DB.submissions.get_title(tag = tag)
        submission_aim = DB.submissions.get_research_aim(tag = tag)
        results.append(SubmissionTitleAndAimOutput(
                submission_tag=tag,
                title=submission_title,
                research_aim=submission_aim
            ))
    print("called", "results: ", results    )
    return results
    
@tool("count_submissions")
def count_submissions() -> int:
    """Returns total number of submissions."""
    return DB.submissions.count()


@tool("count_submissions_by_query")
def count_submissions_by_query(
    current_user_tag : str,
    search_string: str = None,
    state: str = None,
    user_tags: List[str] = None
) -> Dict[str, int]:
    """Returns query_count and total_count for filters."""

    total_count = DB.submissions.count()

    matches = DB.submission_filter.find(
        current_user_tag=current_user_tag,
        search_string=search_string,
        state=state,
        user_tags=APIParamString(param=user_tags).param,
        limit=None
    )

    return {
        "query_count": len(matches),
        "total_count": total_count
    }


# =========================================================
# 2. BASIC SUBMISSION INFO
# =========================================================

@tool("submission_exists", args_schema=SubmissionTagInput)
def submission_exists(submission_tag: str) -> bool:
    """Check if a submission exists."""
    return DB.submissions.exists(tag=submission_tag)

@tool("get_submission_state", args_schema=SubmissionTagInput)
def get_submission_state(submission_tag: str) -> str:
    """Get submission state."""
    if not DB.submissions.exists(tag=submission_tag):
        return "NOT_FOUND"
    return DB.submissions.get_state(tag=submission_tag)


@tool("get_submission_created_at", args_schema=SubmissionTagInput)
def get_submission_created_at(submission_tag: str) -> float:
    """Get creation timestamp. Use this to determine when a submission was created."""
    if not DB.submissions.exists(tag=submission_tag):
        return -1
    return DB.submissions.get_created_at(tag=submission_tag)

@tool("get_submission_creator", args_schema=SubmissionTagInput)
def get_submission_creator(submission_tag: str) -> Tuple[str,str]:
    """Get the user tag that created the submission. This must be called when you want to find the name of the creator of a submission. It returns the user_tag and the user name as <firstname> <lastname> <email>. If the submission does not exist, it returns 'NOT_FOUND'."""
    if not DB.submissions.exists(tag=submission_tag):
        return "NOT_FOUND", "NOT_FOUND"
    user_tag = DB.submissions.get_creator(tag=submission_tag)
    user = DB.users.get_user_by_tag(tag = user_tag)
    return user_tag, f"{user.firstname} {user.lastname} ({user.email})" if user else "NOT_FOUND"


@tool("get_submission_user_team", args_schema=SubmissionTagInput)
def get_submission_user_team(submission_tag: str) -> List[Tuple[str, str]]:
    """Get the all users of a submission. Returns a list of tuples containing user_tag and user name as <firstname> <lastname> <email>. This includes the creator of the submission and all collaborators. If the submission does not exist, it returns an empty list."""
    if not DB.submissions.exists(tag=submission_tag):
        return []
    user_tags = DB.submissions.get_users(tag=submission_tag)
    collaborators = []
    for user_tag in user_tags:
        user = DB.users.get_user_by_tag(tag=user_tag)
        collaborators.append((user_tag, f"{user.firstname} {user.lastname} ({user.email})" if user else "NOT_FOUND"))
    return collaborators

@tool("get_submission_attributes", args_schema=SubmissionConditionApplicationInput)
def get_submission_attributes(submission_tag: str, attribute_tags : List[str] = None, group_by_min_state: bool = False, group_by_attribute: bool = False) -> List[str]:
    """Get attribute tags of a submission."""
    if not DB.submissions.exists(tag=submission_tag):
        return []
    return DB.submissions.get_conditions_applications(tag=submission_tag, group_by_attribute=group_by_attribute, group_by_min_state=group_by_min_state, attribute_tags=attribute_tags)


# =========================================================
# 3. SAMPLES
# =========================================================

@tool("get_submission_samples")
def get_submission_samples(submission_tag: str) -> List[str]:
    """Returns sample tags for a submission."""
    if not DB.submissions.exists(tag=submission_tag):
        return []
    return DB.submissions.get_samples(tag=submission_tag)


@tool("get_submission_samples_full")
def get_submission_samples_full(submission_tag: str) -> List[Dict]:
    """Returns samples with genotype and basic info."""
    if not DB.submissions.exists(tag=submission_tag):
        return []

    result = []
    sample_tags = DB.submissions.get_samples(tag=submission_tag)

    for sample_tag in sample_tags:
        sample = DB.samples.get(tag=sample_tag)
        genotype = DB.samples.get_sample_genotype(tag=sample_tag)

        result.append({
            "tag": sample_tag,
            "index": sample.get("index") if sample else None,
            "genotype": genotype
        })

    return result


# =========================================================
# 4. CONDITION APPLICATIONS
# =========================================================

@tool("get_submission_condition_applications")
def get_submission_condition_applications(submission_tag: str) -> List[str]:
    """Returns condition application tags for a submission."""
    if not DB.submissions.exists(tag=submission_tag):
        return []

    return DB.submissions.get_conditions_applications(tag=submission_tag)


@tool("get_submission_ca_attributes")
def get_submission_ca_attributes(submission_tag: str) -> List[str]:
    """Returns CA attribute tags for submission."""
    if not DB.submissions.exists(tag=submission_tag):
        return []

    ca_tags = DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=False)
    attribute_tags = [
        DB.condition_applications.get_attribute(ca_tag)
        for ca_tag in ca_tags
    ]

    return [a for a in attribute_tags if a is not None]

@tool("get_submission_title")
def get_submission_title(submission_tag: str) -> str:
    """Get submission title."""
    if not DB.submissions.exists(tag=submission_tag):
        return "NOT_FOUND"
    return DB.submissions.get_title(tag=submission_tag)

# =========================================================
# 6. RUNLIST
# =========================================================

@tool("get_submission_runlist")
def get_submission_runlist(submission_tag: str) -> Dict:
    """Returns runlist for submission."""

    if not DB.submissions.exists(tag=submission_tag):
        return {}

    runlist = DB.submissions.get_runlist(submission_tag=submission_tag)
    if runlist is None:
        return {}

    return runlist.model_dump()





SUBMISSION_TOOLS = [find_submissions, 
                    get_submission_title_and_research_aim, 
                    get_submission_creator, 
                    get_submission_user_team, 
                    get_submission_attributes, 
                    get_submission_samples, 
                    get_submission_samples_full, 
                    get_submission_condition_applications, 
                    get_submission_ca_attributes, 
                    get_submission_runlist, 
                    submission_exists,
                    get_submission_title, 
                    get_submission_state, 
                    get_submission_created_at]