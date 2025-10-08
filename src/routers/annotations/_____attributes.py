from fastapi import APIRouter , Depends 

from typing import List

from config.models.user import UserModel
from config.models.attributes import AttributeModel, AttributeValueModel, AttributeResponseModel

from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from services.enums import get_enum_as_dict
import pandas as pd


from lib.database.Database import Database 

DB = Database.DB() 


router = APIRouter(
    prefix="/api",
    tags=["Attributes"]
    )


# @router.get("/attributes", response_model=AttributeResponseModel)
# def get_attributes(user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
#     """
#     Returns the stored attribute and attribute values.
#     """
    
#     attributes = DB.attributes.get()
#     attribute_values = DB.attributes.values(tags = [a.tag for a in attributes])
#     print(attributes)
#     #db_attributes = MCAttributes.getAttributeDatabase()

#     return AttributeResponseModel(attributes=attributes,
#                                   attribute_values=attribute_values)


# @router.get("/attributes/user", response_model=AttributeResponseModel)
# def get_user_attributes(user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
#     """
#     Returns the stored attribute and attribute value definitions that can be assigned to a user.
#     """
    
#     attributes = DB.attributes.get_attributes_for_user()
#     attribute_values = DB.attributes.values(tags = [a.tag for a in attributes])
#     #db_attributes = MCAttributes.getAttributeDatabase()

#     # attributes = db_attributes.getAttributes()
#     # attributes = attributes.loc[attributes["allow_for_user"], :]

#     # attribute_values = db_attributes.getAttributeValues()
#     # attribute_values = attribute_values.loc[attribute_values["attribute_id"].isin(attributes["id"].values)]

#     # Todo: Do not understand what you mean with that.
#     # if user.role == UserRolesEnum.ADMIN:
#     #     # only admin can change the user role
#     #     max_attr_value_id = db.attribute_values["id"].max()
#     #     role_attr = [attr for attr in attrs if attr.tag == "att_user_role"][0]
#     #     user_roles = get_enum_as_dict(UserRolesEnum)
#     #     attrValues.extend([{"id" : max_attr_value_id + 1, "attribute_id" : role_attr.id, "details" : role_name.title(), "name" : role, "tag" : f"att_user_role:{role}"} for n,(role_name, role) in enumerate(user_roles.items())])
#     # else:
#     #     attrs = [attr for attr in attrs if attr.tag != "att_user_role"]

#     return AttributeResponseModel(attributes=attributes,
#                                   attribute_values=attribute_values)


# @router.post("/attributes")
# def add_attribute(attribute : AttributeModel) -> List[AttributeModel]:
#     """Adds an attribute and returns the updated list"""
#     #ToDo: implement adding attributes from the GUI. 
#     db_attributes = MCAttributes.getAttributeDatabase()
#     return [AttributeModel(**item) for item in db_attributes.getAttributes().to_dict(orient="records")]
#     # return db_attributes.getAttributes().to_dict(orient="records")  # ToDo: How to cast into a AttributeModel?


# @router.get("/attributes/{attribute_id}")
# def get_attribute_by_id(attribute_id : int) -> AttributeModel:  # ToDo: Do you mean the numerical ID or the tag?, ID, these were placeholders from the very beginning, changed them
#     """
#     Returns the attribute by its ID
#     """
#     return {}

# @router.get("/attributes/{attribute_tag}")
# def get_attribute_by_name(attribute_tag : str) -> AttributeModel:  # ToDo: Do you mean the numerical ID or the tag?, the tag, changed. 
#     """
#     Returns a single attribute by its tag
#     """
#     return {}

# @router.delete("/attributes/{attribute_id}")
# def delete_attribute_by_id(attribute_id : int) -> dict:
#     """Deletes an attribute by ID"""
#     return {}  # ToDo: What should be returned? deleted attributes? Tag or IDs?

