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
    prefix="/api/features/protein_groups",
    tags=["Features", "Protein Groups"]
    )


@router.get("/{protein_group_tag}/text}", summary="Get the protein group text.")
def get_protein_group_text(protein_group_tag : str, user: UserModel = Depends(get_user_from_token)) -> str:
    """_summary_

    Parameters
    ----------
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    str
        _description_
    """
    protein_tags = DB.protein_groups.get_proteins(tag = protein_group_tag)
    t = ", ".join([DB.proteins.get(tag = pt).gene_name for pt in protein_tags])
    
    
