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
from config.models.feature import FeatureNeoModel
DB = Database.DB()


router = APIRouter(
    prefix="/api/features/proteins",
    tags=["Features", "Proteins"]
    )


@router.get("/{tag}", summary="Returns the protein information model.")
def get_protein_features(tag: str, user: UserModel = Depends(get_user_from_token)) -> FeatureNeoModel:
    """
    Returns the protein information model.
    
    Parameters
    ----------
    tag : str
        The tag of the protein to retrieve.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    FeatureNeoModel
        The protein information model.
    """

    return DB.proteins.get(tag = tag)
    
