from fastapi import APIRouter , Depends 

from typing import List

from config.models.user import User
from config.models.attributes import AttributeModel, AttributeValueModel, AttributeResponseModel
from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from services.enums import get_enum_as_dict
import pandas as pd 

router = APIRouter(
    prefix="/api",
    tags=["Attributes"]
    )


@router.get("/attributes", response_model=AttributeResponseModel)
def get_attributes(user : User = Depends(get_user_from_token)) -> AttributeResponseModel:
    """
    Returns the stored attribute and attribute value definitions.
    """
    db_attributes = MCAttributes.getAttributeDatabase()

    return AttributeResponseModel(attributes=db_attributes.getAttributes().to_dict(orient="records"),
                                  attribute_values=db_attributes.getAttributeValues().to_dict(orient="records"))


@router.get("/attributes/user", response_model=AttributeResponseModel)
def get_user_attributes(user : User = Depends(get_user_from_token)) -> AttributeResponseModel:
    """
    Returns the stored attribute and attribute value definitions that can be assigned to a user.
    """
    db_attributes = MCAttributes.getAttributeDatabase()

    attributes = db_attributes.getAttributes()
    attributes = attributes.loc[attributes["allow_for_user"], :]

    attribute_values = db_attributes.getAttributeValues()
    attribute_values = attribute_values.loc[attribute_values["attribute_id"].isin(attributes["id"].values)]

    # Todo: Do not understand what you mean with that.
    # if user.role == UserRolesEnum.ADMIN:
    #     # only admin can change the user role
    #     max_attr_value_id = db.attribute_values["id"].max()
    #     role_attr = [attr for attr in attrs if attr.tag == "att_user_role"][0]
    #     user_roles = get_enum_as_dict(UserRolesEnum)
    #     attrValues.extend([{"id" : max_attr_value_id + 1, "attribute_id" : role_attr.id, "details" : role_name.title(), "name" : role, "tag" : f"att_user_role:{role}"} for n,(role_name, role) in enumerate(user_roles.items())])
    # else:
    #     attrs = [attr for attr in attrs if attr.tag != "att_user_role"]

    return AttributeResponseModel(attributes=attributes.to_dict(orient="records"),
                                  attribute_values=attribute_values.to_dict(orient="records"))


@router.post("/attributes")
def add_attribute(attribute : AttributeModel) -> List[AttributeModel]:
    """Adds an attribute and returns the updated list"""

    db_attributes = MCAttributes.getAttributeDatabase()

    return [AttributeModel(**item) for item in db_attributes.getAttributes().to_dict(orient="records")]
    # return db_attributes.getAttributes().to_dict(orient="records")  # ToDo: How to cast into a AttributeModel?


@router.get("/attributes/{attribute_id}")
def get_attribute_by_id(attribute_id : str) -> AttributeModel:  # ToDo: Do you mean the numerical ID or the tag?
    """
    Returns the attribute by its ID
    """
    return {}

@router.get("/attributes/{attribute_name}")
def get_attribute_by_name(attribute_name : str) -> AttributeModel:  # ToDo: Do you mean the numerical ID or the tag?
    """
    Returns attribute by its name
    """
    return {}

@router.delete("/attributes/{attribute_id}")
def delete_attribute_by_id(attribute_id : str) -> dict:
    """Deletes an attribute by ID"""
    return {}  # ToDo: What should be returned? deleted attributes? Tag or IDs?

