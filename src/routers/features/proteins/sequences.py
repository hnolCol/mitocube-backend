from fastapi import APIRouter, Depends, HTTPException
from typing import List
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.feature import FeatureSequenceResponseModel
from config.models.annotations.feature import FeatureDataResponseModel, FeatureNeoModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
from config.models.parameter import APIParamString
from config.models.calculations.quantile import QuantileModel 

from lib.database.Database import Database

from config.exceptions.HTTPExceptions import protein_not_found
from collections import OrderedDict
DB = Database.DB()


router = APIRouter(
    prefix="/api/features/proteins",
    tags=["Features", "Proteins","Sequences"]
    )



@router.get("/{tag}/sequences")
def get_protein_sequences(tag: str, user: UserModel = Depends(get_user_from_token)) -> str:
    """
    Returns the protein sequences for a given tag.
    """
    
    if DB.features.exists(tag=tag) is False:
        raise HTTPException(status_code=404, detail="Protein not found") 
    
    
@router.get("/{tag}/sequence_coverage")
def get_protein_sequence_coverage(tag: str, user: UserModel = Depends(get_user_from_token)) -> float:
    """
    Returns the sequence coverage for a given protein tag.
    """
    
    if DB.features.exists(tag=tag) is False:
        raise HTTPException(status_code=404, detail="Protein not found") 
    
    coverage = DB.features.get_protein_sequence_coverage(tag=tag)
    
    return coverage


