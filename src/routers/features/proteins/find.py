from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal

# 
from lib.database.Database import Database
import pandas as pd 
from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel, NewsInsertModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator
from config.enums.states import SubmissionStatesEnums 
from config.models.plots.stats import DistResponseModel
DB = Database.DB()


router = APIRouter(
    prefix="/api/features/proteins",
    tags=["Features", "Proteins"]
    )


@router.get("/q", summary="Finds proteins by search query.")
def bulk_insert_protein_features(search_string : str, limit : int = None, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """
    Bulk insert of new protein features. Requires curator rights.
    
    Parameters
    ----------
    search_string : str
        The search string to find proteins.
    limit : int, optional
        The limit of proteins to return, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_cur
    Returns
    -------
    List[str]
       Protein tags
    """
    return DB.proteins.find(search_string=search_string, limit=limit)
    
