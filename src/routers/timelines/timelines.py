
from typing import List
from fastapi import APIRouter, Depends
from config.models.user import UserModel, PublicUser
from config.models.timeline import SubmissionTimelineResponseModel, TimelineModel, TimelineInputModel
from services.users import get_user_from_token, is_user_at_least_curator
from lib.database.Database import Database

DB = Database.DB()

router = APIRouter(
    prefix="/api/timelines",
    tags=["Timeline","Submission"],
    )


@router.get("")
def get_time_line_events(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[TimelineModel]:
    ""
    print(DB.timeline.get_timeline_by_submission_tag(submission_tag = submission_tag))
    return DB.timeline.get_timeline_by_submission_tag(submission_tag = submission_tag)
    
    


@router.post("/")
def insert_time_line_even(content : str, submission_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    ""
    submission_state = DB.submission.get_state(tag = submission_tag)
    timeline_input = TimelineInputModel(user_tag = user.tag, content = content, submission_tag = submission_tag, submission_state = submission_state)
    DB.timeline.insert(timeline_input)
    
    
    