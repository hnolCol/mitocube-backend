from fastapi import APIRouter, Depends
from typing import List, Annotated

from lib.data.database.ABCDatabase import MCDatabase 

from config.enums.users.roles import UserRolesEnum
from config.models.user import User
from config.models.submissions.submissions import SubmissionResponse, SubmissionIDResponse

from services.users import get_user_from_token

router = APIRouter(
    prefix="/api/submission",
    tags=["Submission"],
    )


@router.get("/id",
    summary = "Returns a unique id for a new submission.",
    response_model = SubmissionIDResponse)
def get_submission_id():
    """
    A unique id that cannot be changed for a project/data/submission.
    """
    return SubmissionIDResponse()


@router.get("/submissions")
def get_submission(user : User = Depends(get_user_from_token)):
    """
    Returns the submissions depending on the user's role. 
    Curators and admins are able to see all submissions
    while standard users can only see their own submissions
    """
    db = MCDatabase.getDatabase()
    metadata = db.getJSONDatasets()
    if user.role < UserRolesEnum.CURATOR:
        return [dataset_meta for dataset_meta in metadata if dataset_meta.user_label == user.label] #check if in a list of collaborators ? 
    else:
        #return all if user at least curator
        return metadata 