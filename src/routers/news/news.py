from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List

# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.data.database.Database import Database

from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token

DB = Database.DB()


router = APIRouter(
    prefix="/api/news",
    tags=["News"]
    )

@router.get("")
def get_news(tags : str = None, limit : int = 10, user : UserModel = Depends(get_user_from_token)) -> List[NewsModel]:
    """_summary_

    Parameters
    ----------
    tags : str, optional
        The tags you want to receive the news for. For multiple, separate by ';', by default None
    limit : int, optional
        _description_, by default 10
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    List[News]
        _description_
    """
    
    return DB.news.get(tags = APIParamString(param = tags).param, limit=limit)