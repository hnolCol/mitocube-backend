from fastapi import APIRouter , Depends 

from typing import List

from config.models.user import User
from config.models.attributes import Attribute
from lib.data.database.ABCDatabase import MCDatabase

from services.users import get_user_from_token


router = APIRouter(
    prefix="/api",
    tags=["Attributes"]
    )


@router.get("/attributes")
def get_attributes(user : User = Depends(get_user_from_token)) -> {}:
    """
    Returns the stored attributes 
    """
    print(user)
    db  = MCDatabase.getDatabase()
    attributes = db.attributes
    attribute_values = db.attribute_values 
    print(attributes)
    print(attribute_values)
    return {"attributes" : attributes.to_dict(orient="records"), "attribute_values" : attribute_values.to_dict(orient="records")}

@router.post("/")
def add_attribute(attribute : Attribute) -> List[Attribute]:
    """Adds an attribute and returns the updated list"""
    return []


@router.get("/{attribute_id}")
def get_attribute_by_id(attribute_id : str) -> Attribute:
    """
    Returns the attribute by its ID
    """
    return {}

@router.get("/{attribute_name}")
def get_attribute_by_name(attribute_name : str) -> Attribute:
    """
    Returns attribute by its name
    """
    return {}

@router.delete("/{attribute_id}")
def delete_attribute_by_id(attribute_id : str) -> dict:
    """Deletes an attribute by ID"""
    return {}


