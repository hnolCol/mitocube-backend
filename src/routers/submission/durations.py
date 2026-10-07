from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions/durations",
    tags=["Submission","Durations"],
    )

@router.get("/average")
def get_average_submission_duration(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> float:
    "Return the average duration of submissions in days" 
    return db.submissions.get_duration_between_states(state_01=SubmissionStatesEnums.SUBMITTED, state_02=SubmissionStatesEnums.DONE)