from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/durations",
    tags=["Submission","Durations"],
    )

@router.get("/average")
def get_average_submission_duration(user : UserModel = Depends(get_user_from_token)) -> float:
    "Return the average duration of submissions in days" 
    return DB.submissions.get_duration_between_states(state_01=SubmissionStatesEnums.SUBMITTED, state_02=SubmissionStatesEnums.DONE)