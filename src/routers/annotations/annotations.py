
from fastapi import APIRouter , Depends 

import pandas as pd 
from typing import List, Optional

# from lib.data.annotations.ABCAnnotations import AnnotationSettings
from config.models.user import BasicUserWithEmail
from config.models.annotations.feature import FeatureModel
from config.models.attributes import AttributeValueModel, AttributeModel
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from services.users import get_user_from_token


router = APIRouter(
    prefix="/api/annotations",
    tags=["Attributes"]
    )




@router.get('/features',  # /api/annotations/features
            summary="Returns all features that are present in the database (Uniprot downloaded for available organisms).",
            response_model=List[FeatureModel])
def get_features_in_database(proteome_ids : str = None, user : BasicUserWithEmail = Depends(get_user_from_token)) :
    """
    Returns all features that are present in the database (Uniprot downloaded for available organisms). 
    This is not the list of features present in the datasets but rather the features that are annotation information exist for and
    the reference proteome consists of. 
    

    API Endpoint
    ------------
    The API endpoint of this route HTTP method is : 
    ``GET  /api/annotations/features``

    Parameters
    ----------
    proteome_id : str, default None
        Uniprot reference proteome. 
    user : BasicUserWithEmail 
        The user extracted from the token using FastAPI Depends function 


    Returns
    -------
    List[FeatureModel]
        The list of features available in the database if no organism is provided. If provided
        returns the list of features for a specific organism. 

    """
    if proteome_ids is not None:
        proteome_ids = proteome_ids.split(";")
    db_features = PandaFeatureDatabase()
    features = db_features.get(proteome_ids=proteome_ids)
       
    features = features.reset_index(names="key")
    features = features.to_dict(orient="records")  # [{'col1': 1, 'col2': 0.5}, {'col1': 2, 'col2': 0.75}]
    return [FeatureModel(**item) for item in features] 
