from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal, Dict

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
from config.models.feature import ProteinGroupSubmissionStatisticsModel
DB = Database.DB()


router = APIRouter(
    prefix="/api/features/protein_groups",
    tags=["Features", "Protein Groups"]
    )



@router.get("/{protein_group_tag}/stats", summary="Returns the statistics for a given protein group.")
def get_protein_group_stats(protein_group_tag : str, attribute_tags : str = None, ca_tags : str = None, include_sample_ca : bool = True, user_tags : str = None, user : UserModel = Depends(get_user_from_token), limit : int = None) -> List[ProteinGroupSubmissionStatisticsModel]:
    
    if not DB.protein_groups.exists(tag = protein_group_tag): #check if protein group exists, otherwise raise 404
        raise HTTPException(status_code=404, detail="Protein group not found")
    
    submission_tags = None 
    parsed_ca_tags = APIParamString(param=ca_tags).param
    if parsed_ca_tags is not None and len(parsed_ca_tags) > 0:
        submission_tags = DB.submission_filter.filter_by_condition_applications(
            ca_tags=parsed_ca_tags,
            include_sample_ca=include_sample_ca,
            match_all=True,
            ordered=False
        )
        if len(submission_tags) == 0:
            return []  # No submissions match the given condition applications
    
    parsed_user_tags = APIParamString(param=user_tags).param
    if parsed_user_tags is not None and len(parsed_user_tags) > 0:
        submission_tags = DB.submission_filter.filter_by_user(
            user_tags=parsed_user_tags,
            submission_tags=submission_tags,
            role="any",
            ordered=False,
        )
        if len(submission_tags) == 0:
            return [] # No submissions match the given user tags

        
    r=DB.protein_groups.get_statistical_ranking(tag=protein_group_tag, attribute_tags=APIParamString(param=attribute_tags).param, submission_tags=submission_tags, limit=limit)
    return r
        
    
    

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
    return t 

    
@router.get("/protein/{protein_tag}", summary="Get protein groups containing a given protein.")
def get_protein_groups_by_protein(protein_tag: str, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    if not DB.proteins.exists(protein_tag):
        raise HTTPException(status_code=404, detail="Protein not found")
    return DB.protein_groups.get_protein(protein_tag)