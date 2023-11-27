from fastapi import APIRouter , Depends 

from typing import List

from config.models.user import User
from config.models.attributes import Attribute, AttributeValue, AttributeResponse
from lib.data.database.ABCDatabase import MCDatabase

from services.users import get_user_from_token

import pandas as pd 

router = APIRouter(
    prefix="/api",
    tags=["Attributes"]
    )


@router.get("/attributes", response_model=AttributeResponse)
def get_attributes(user : User = Depends(get_user_from_token)) -> AttributeResponse:
    """
    Returns the stored attributes 
    """
    db  = MCDatabase.getDatabase()
    attributes = db.attributes
    attribute_values = db.attribute_values 
    return {"attributes" : [Attribute(**x) for x in attributes.to_dict(orient="records")], "attribute_values" : attribute_values.to_dict(orient="records")}


@router.get("/attributes/user", response_model=AttributeResponse)
def get_attributes(user : User = Depends(get_user_from_token)) -> AttributeResponse:
    """
    Returns the stored attributes 
    """
    db  = MCDatabase.getDatabase()
    attributes = db.attributes.loc[db.attributes["allow_for_user"],:]
    attribute_values = db.attribute_values.loc[db.attribute_values["attribute_id"].isin(attributes["id"].values)]
    #print([Attribute(**x) for x in attributes.to_dict(orient="records")])
    return {"attributes" : [Attribute(**x) for x in attributes.to_dict(orient="records")], "attribute_values" : attribute_values.to_dict(orient="records")}


@router.post("/attributes")
def add_attribute(attribute : Attribute) -> List[Attribute]:
    """Adds an attribute and returns the updated list"""
    return []


@router.get("/attributes/{attribute_id}")
def get_attribute_by_id(attribute_id : str) -> Attribute:
    """
    Returns the attribute by its ID
    """
    return {}

@router.get("/attributes/{attribute_name}")
def get_attribute_by_name(attribute_name : str) -> Attribute:
    """
    Returns attribute by its name
    """
    return {}

@router.delete("/attributes/{attribute_id}")
def delete_attribute_by_id(attribute_id : str) -> dict:
    """Deletes an attribute by ID"""
    return {}


