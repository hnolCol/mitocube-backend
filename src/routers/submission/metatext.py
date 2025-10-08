

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.submissions.metatexts import MetaTextInsertModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_at_least_curator

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Metatext", "Submissions"],
    )

@router.post("/{submission_tag}/metatext")
def create_submission_metatext(submission_tag: str, metatext : MetaTextInsertModel, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Create a new metatext for a given submission."

    ok = DB.metatexts.insert(title=metatext.title, text=metatext.text, submission_tag=submission_tag, user_tag=user.tag)
    return ok
