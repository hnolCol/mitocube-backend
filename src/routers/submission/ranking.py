
from typing import List

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from services.users import get_user_from_token
from config.models.feature import ExclusivelyQuantifiedModel
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Ranking", "Submissions"],
    )

@router.get("/{tag}/ranking")
def get_ranking(tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Create a new metatext for a given submission."
    DB.protein_groups.get_statistical_ranking()
    
    
    
@router.get("/{tag}/ranking/exclusively_quantified")
def get_exclusively_quantified(tag : str, limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[ExclusivelyQuantifiedModel]:
    "Get the exclusively quantified proteins for a given submission."
    return DB.protein_groups.get_exclusively_quantified(submission_tag = tag)
