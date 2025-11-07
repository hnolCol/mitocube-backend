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
    prefix="/api/stats/submissions",
    tags=["Features","Statistics"]
    )



@router.get("/proteins/{feature_tag}/views ")
def get_protein_views(feature_tag: str, user: UserModel = Depends(get_user_from_token)) -> int:
    """
    Returns the number of views for a given protein feature tag.
    """
    if DB.features.exists(tag=feature_tag) is False:
        raise HTTPException(status_code=404, detail="Protein not found")

    views = DB.features.get_protein_views(tag=feature_tag)

    return views



