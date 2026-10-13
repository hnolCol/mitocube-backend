from pydantic import BaseModel, Field
from typing import Optional

from services.date import get_time_stamp


class CollaborationRequestModel(BaseModel):
    """A collaboration request for a submission, created by a user that
    wants to collaborate on a submission they do not have access to."""
    tag : str = Field(..., description="Unique tag of the collaboration request.")
    submission_tag : str
    requested_by : str
    created_at : float = Field(..., default_factory=get_time_stamp)
    requested_for_user_tag : Optional[str] = None
    requested_for_group_tag : Optional[str] = None
    message : Optional[str] = None
    status : str = "pending"


class CollaborationRequestInput(BaseModel):
    """Input model to create a collaboration request."""
    submission_tag : str
    message : Optional[str] = None
    requested_for_user_tag : Optional[str] = None
    requested_for_group_tag : Optional[str] = None


class SubmissionExploreModel(BaseModel):
    """Minimal metadata of a submission as returned by the explore endpoint.
    Deliberately contains only non-sensitive, discoverable fields."""
    tag : str
    title : str
    state : Optional[int] = None
    created_at : Optional[float] = None
    owner_tag : Optional[str] = None
    owner_firstname : Optional[str] = None
    owner_lastname : Optional[str] = None
    owner_institute : Optional[str] = None
    research_group_tag : Optional[str] = None
    research_group_text : Optional[str] = None
    research_group_institute : Optional[str] = None
    has_open_collaboration_request : bool = False
