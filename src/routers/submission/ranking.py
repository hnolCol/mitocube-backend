
from typing import List
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from config.models.user import UserModel
from services.users import get_user_from_token
from services.submission import check_submission_access
from config.models.feature import ExclusivelyQuantifiedModel
from config.models.parameter import APIParamString

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions",
    tags=["Ranking", "Submissions"],
    )

@router.get("/{tag}/ranking")
def get_ranking(tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    "Create a new metatext for a given submission."
    check_submission_access(submission_tag = tag, user = user, db = db)
    db.protein_groups.get_statistical_ranking()
    
    
    
@router.get("/{tag}/ranking/exclusively_quantified")
def get_exclusively_quantified(tag : str, annotation_tags : str = None, limit : int = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[ExclusivelyQuantifiedModel]:
    "Get the exclusively quantified proteins for a given submission."
    check_submission_access(submission_tag = tag, user = user, db = db)
    return db.protein_groups.get_exclusively_quantified(submission_tag = tag, annotation_tags = APIParamString(param=annotation_tags).param, limit = limit)
