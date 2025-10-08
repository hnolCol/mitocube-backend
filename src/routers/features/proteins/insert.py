from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal

# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
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


@router.post("/", summary="Bulk insert of new protein features. Requires curator rights.")
def bulk_insert_protein_features(features: List, user: UserModel = Depends(is_user_at_least_curator)) -> int:
    """
    Bulk insert of new protein features. Requires curator rights.
    
    Parameters
    ----------
    features : List
        List of protein features to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)
    Returns
    -------
    int
        Number of inserted protein features.
    """
    if not is_user_at_least_curator(user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return DB.features.bulk_insert_proteins(features)
    
