

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.submissions.metatexts import MetaTextInsertModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_at_least_curator, is_creator_of_submission_or_curator
from services.submission import check_submission_access


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions",
    tags=["Metatext", "Submissions"],
    )

@router.post("/{submission_tag}/metatext")
def create_submission_metatext(submission_tag: str, metatext : MetaTextInsertModel, user : UserModel = Depends(is_creator_of_submission_or_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Create a new metatext for a given submission."

    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    ok = db.metatexts.insert(title=metatext.title, text=metatext.text, submission_tag=submission_tag, user_tag=user.tag)
    return ok
