from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationAttributeModel
from services.users import get_user_from_token
from lib.database.Database import get_db
from typing import List, Dict, Literal

router = APIRouter(dependencies=[Depends(get_user_from_token)],

    prefix="/api/users",
    tags=["Condition Applications"],
    
)

@router.get("/views")
def get_last_views(type : Literal["submissions"], limit : int = 20, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:    
    """
    Return the last views of the user.

    Parameters
    ----------
    
    type : Literal["submissions","features"]
        The type of views to return. Can be "submissions" or "features". 
    limit : int, optional
        The maximum number of views to return, by default 20
    user : UserModel, optional
        The user identified using the jwt token, by default Depends(get_user_from_token)
    db : DatabaseABC, optional
        The database, by default Depends(get_db)

    Notes
    -----
    Only the authenticated user's own views are returned; querying another
    user's tag is not supported (IDOR).
    """
    if type == "submissions":
        return db.users.get_user_submission_views(tag = user.tag, limit = limit)
    return []
