

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.submissions.metatexts import MetaTextInsertModel
from config.models.user import UserModel
from services.users import get_user_from_token
from config.exceptions.HTTPExceptions import submission_tag_not_found
from config.models.submissions.metatexts import ResearchAimInsertModel



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions",
    tags=["Research Aim", "Submissions"],
    )

@router.get("/{submission_tag}/researchaim")
def create_submission_metatext(submission_tag: str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> str:
    "Create a new metatext for a given submission."
    if not db.submissions.exists(tag = submission_tag):
        raise submission_tag_not_found
    research_aim_text = db.submissions.get_research_aim(tag=submission_tag)
    if research_aim_text is None:
        raise HTTPException(status_code=404, detail="No research aim found for this submission.")   
    return research_aim_text



@router.post("/{submission_tag}/researchaim")
def set_submission_research_aim(submission_tag: str, research_aim : ResearchAimInsertModel, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    "Set the research aim for a given submission."
    if not db.submissions.exists(tag = submission_tag):
        raise submission_tag_not_found
    return db.submissions.insert_research_aim(tag=submission_tag, research_aim=research_aim.research_aim, user_tag=user.tag)



@router.patch("/{submission_tag}/researchaim")
def update_submission_research_aim(submission_tag: str, research_aim: ResearchAimInsertModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    "Update the research aim for a given submission. This will replace any existing research aim."
    if not db.submissions.exists(tag=submission_tag):
        raise submission_tag_not_found
    return db.submissions.insert_research_aim(tag=submission_tag, research_aim=research_aim.research_aim, user_tag=user.tag)


