from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/counts",
    tags=["Submission"],
    )

@router.get("/states/{state_tag}")
def get_submission_state_count(state_tag : SubmissionStatesEnums, user : UserModel = Depends(get_user_from_token)) -> int:
    "Return the number of submissions in a given state" 
    return DB.submissions.count(state=state_tag)



@router.get("/{submission_tag}/proteins") 
def get_protein_count_for_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "Return the number of proteins for a given submission"
    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")
    return DB.protein_groups.count(submission_tag=submission_tag)