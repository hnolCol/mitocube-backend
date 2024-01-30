
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
def get_features_in_database(proteome_id : Optional[str] = None, user : BasicUserWithEmail = Depends(get_user_from_token)) :
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
    db_features = PandaFeatureDatabase()
    features = db_features.get(proteome_id=proteome_id) #if organism is provided. 
       
    features = features.reset_index(names="key")
    features = features.to_dict(orient="records")  # [{'col1': 1, 'col2': 0.5}, {'col1': 2, 'col2': 0.75}]
    return [FeatureModel(**item) for item in features] 





@router.post('/features/attributeValues',  # /api/annotations/features/attributeValues
             summary="Returns all features that are present in the database in the format for attribute value selection.",
             response_model=List[AttributeValueModel])
def get_features_in_database_as_values(organisms : List[AttributeValueModel], user : BasicUserWithEmail = Depends(get_user_from_token)) :
    """
    Returns all features that are present in the database in the format for attribute value selection.
    This is intended to be used for attributes that have has_features_value = True to provide a list of 
    features to define a gene knockout or knockdown. 

    API Endpoint
    ------------
    The API endpoint of this ``POST`` method route is: 
    /api/annotations/features/attributeValues

    Parameters
    ----------
    organisms : List[AttributeModel], default None
        Organisms provided as attribute values. 
    user : BasicUserWithEmail 
        The user extracted from the token using FastAPI Depends function 


    Returns
    -------
    List[AttributeValueModel]
        The list of features available as an AttributeValueModel. 

    Raises
    ------
        #TODO Add errors when token is invalid and if organism_id is not avaialblabe/defined

    """
    ## add controls somewhere else!! -> in annotation datasets or in the attributes? 
    CONTORLS = [AttributeValueModel(attribute_id=-1, tag=f"att_feature:GFP", name ="GFP", details="GFP Proteins (knock-down control)", id=-2),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:scr", name ="Scrambled", details="Scrambled Protein Sequence", id=-3),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:ctrl", name ="Control", details="Control sgRNA or siRNA", id=-4),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:fluc", name ="FLUC", details="FLUC Protein", id=-1),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:rluc", name ="RLUC", details="RLUC Protein as a control", id=-5)]
    # db = AnnotationSettings.get_annotation_db()
    proteome_ids = [organism.value for organism in organisms]
    # annotations = []
    # for organism in organisms:
    #     organism_id = organism.tag.split(":")[-1].upper()
    #     a = db.get_features_by_organism(organism_id)
    #     annotations.append(a)
    # A = pd.concat(annotations,axis=0,join="outer")
    return {}  # CONTORLS + [AttributeValue(id = n,
    #                       tag = f"att_feature:{x['uniprot_id']}",
    #                       attribute_id= -1,
    #                       name = f"{x['Gene Names']}",
    #                       details=f"{x['uniprot_id']}, {x['Organism']}, {x['Protein names']}") for n,x in enumerate(A.reset_index().to_dict(orient="records"))]
