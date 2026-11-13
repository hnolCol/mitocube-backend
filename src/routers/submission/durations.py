from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import Dict, List

from config.models.parameter import APIParamInt
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

@router.get("/current")
def get_current_state_durations(states : str = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """Returns for every submission currently in one of the given states how long it has been
    in that state, together with its sample count and creator. Defaults to the open work
    states (submitted, processed, measuring, analysis), i.e. the submissions the facility
    has to work on."""
    state_tags = APIParamInt(param = states).param
    states = [SubmissionStatesEnums(state_tag) for state_tag in state_tags] if state_tags is not None else None
    return db.submissions.get_current_state_durations(states = states)
