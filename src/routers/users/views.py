
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationAttributeModel
from services.users import get_user_from_token
from typing import List, Dict, Literal

DB = Database.DB()

router = APIRouter(
    prefix="/api/users",
    tags=["Condition Applications"],
    )

@router.get("/views")
def get_last_views(type : Literal["submissions"], user_tag: str = None, limit : int = 20, user: UserModel = Depends(get_user_from_token)) -> List[str]|List[ConditionApplicationAttributeModel]:
    
    """
    Return the last views of the user.
    Parameters
    ----------  
    type : Literal["submissions","proteins","peptides"]
        The type of views to return. Can be "submissions", "proteins" or "peptides". #,"add :: proteins","peptides"
    user_tag : str, optional
        The tag of the user. If None, the tag of the user from the token is used, by default None
    limit : int, optional
        The maximum number of views to return, by default 20
    user : UserModel, optional
        The user identified using the jwt token, by default Depends(get_user_from_token)
    """
    user_tag = user.tag if user_tag is None else user_tag
    if type == "submissions":
        return DB.users.get_user_submission_views(tag = user_tag, limit = limit)
    
    