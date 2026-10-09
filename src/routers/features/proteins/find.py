from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List, Literal

# 
import pandas as pd 
from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel, NewsInsertModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator
from services.submission import check_submission_tags_access
from config.enums.states import SubmissionStatesEnums 
from config.models.plots.stats import DistResponseModel


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/features/proteins",
    tags=["Features", "Proteins"]
    )


@router.get("/q", summary="Finds proteins by search query.")
def bulk_insert_protein_features(search_string : str, limit : int = 50, submission_tags : str = None, proteome_tags : str = None, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Bulk insert of new protein features. Requires curator rights.
    
    Parameters
    ----------
    search_string : str
        The search string to find proteins.
    limit : int, optional
        The limit of proteins to return, by default None
    submission_tags : str, optional
        Semicolon separated submission tags to filter the search (e.g. proteins quantified in specific submissions), by default None
    proteome_tags : str, optional
        Semicolon separated proteome tags to filter the search, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_cur
    Returns
    -------
    List[str]
       Protein tags
    """
    check_submission_tags_access(submission_tags = submission_tags, user = user, db = db)
    return db.proteins.find(search_string=search_string, limit=limit, proteome_tags=APIParamString(param=proteome_tags).param, submission_tags=APIParamString(param=submission_tags).param)

