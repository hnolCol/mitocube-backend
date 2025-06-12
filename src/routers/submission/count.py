from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/states",
    tags=["Submission"],
    )

@router.get("/{state}/count")
def get_submission_state_count(state : SubmissionStatesEnums, user : UserModel = Depends(get_user_from_token)) -> int:
    "" 
    return DB.submissions.count(state=state)