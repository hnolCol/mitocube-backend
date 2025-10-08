

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationAttributeModel
from services.users import get_user_from_token
from typing import List, Dict

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Condition Applications"],
    )

@router.get("/{submission_tag}/ca")
def get_submission_condition_applications(submission_tag: str, group_by_attribute : bool = False, user: UserModel = Depends(get_user_from_token)) -> List[str]|List[ConditionApplicationAttributeModel]:
    "Return the condition applications for a given submission."
    return DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=group_by_attribute)