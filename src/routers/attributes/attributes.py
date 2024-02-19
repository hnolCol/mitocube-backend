from fastapi import APIRouter, Depends, HTTPException
from typing import List
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.annotations.feature import FeatureDataResponseModel, FeatureModel
from config.models.attributes import AttributeModel
from config.enums.states import SubmissionStates
from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.users import get_user_from_token
from services.submission import map_tags_to_attribute_in_metadata
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.database.ABCDatabase import MCAttributes
from config.models.attributes import AttributeModel, AttributeValueModel, AttributeResponseModel
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from services.submission import map_tags


router = APIRouter(
    prefix="/api/attributes",
    tags=["Attributes"]
    )

@router.get("", response_model=AttributeResponseModel)
def get_attributes(user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
    """
    Returns the stored attribute and attribute values.
    """
    db_attributes = MCAttributes.getAttributeDatabase()

    return AttributeResponseModel(attributes=db_attributes.getAttributes().to_dict(orient="records"),
                                  attribute_values=db_attributes.getAttributeValues().to_dict(orient="records"))


@router.get("/attribute_values/q")
def get_attribute_values(labels : str = None, attribute_value_tag : str = None, attribute_tag : str = None, count : bool = True, max_attributes : int = 999999):
    
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    db_attributes = MCAttributes.getAttributeDatabase() 
    if labels is None:
        labels = ";".join(db_helper.get_all_labels())
    attribute_value_tags, submission_count_by_attribute_value_tag = db_helper.get_attribute_value_tags_by_labels(labels,count=count, attribute_value_subset=attribute_value_tag, attribute_subset = attribute_tag)
    attribute_values = db_attributes.getAttributeValues(tags=list(attribute_value_tags))
    proteome_ids, count = db_helper.get_organisms_by_label(labels)
    attribute_values_by_tag = attribute_values.set_index("tag", drop=False).to_dict(orient="index")
    #check if size is okay because numeric input and features are not in here and we have to create them.
    missing_attribute_value_tags = [attribute_value_tag for attribute_value_tag in attribute_value_tags if attribute_value_tag  not in attribute_values_by_tag]
    
    if len(missing_attribute_value_tags) > 0:
        missing_attributes = {}
        for attribute_value_tag in missing_attribute_value_tags:
            attribute_tag = attribute_value_tag.split(":")[0]
            if attribute_tag not in missing_attributes:
                missing_attributes[attribute_tag] = []
            missing_attributes[attribute_tag].append(attribute_value_tag)
            
        db_feature = PandaFeatureDatabase()
        attribute_values = db_attributes.getAttributeValues()
        attribute_tags = [attribute_value_tag.split(":")[0] for attribute_value_tag in missing_attribute_value_tags]
        
        attributes = db_attributes.getAttributes(tags=list(attribute_tags)).set_index("tag")
        for attribute_tag, missing_attribute_value_tags in missing_attributes.items():
            attribute = attributes.loc[attribute_tag,:].to_dict()
            attr = AttributeModel(**attribute, tag = attribute_tag)
            missing_attributes = map_tags(attribute=attr, 
                                          attr_value_tags=missing_attribute_value_tags, 
                                          proteome_ids=[tag.split(":")[1] for tag in proteome_ids], 
                                          attribute_values=attribute_values, 
                                          db_features=db_feature)
            for n,missing_attribute_value_tag in enumerate(missing_attribute_value_tags):
                attribute_values_by_tag[missing_attribute_value_tag] = missing_attributes[n]
    
    return {"attribute_value_tags" : attribute_value_tags, "submission_count" : submission_count_by_attribute_value_tag, "attribute_values_by_tag" : attribute_values_by_tag}
    
@router.get("/q")
def get_attributes(labels : str, count : bool = True, max_attributes : int = 999999):
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    db_attributes = MCAttributes.getAttributeDatabase() 
    attribute_tags, submission_count_by_attribute_value_tag = db_helper.get_attribute_tags_by_labels(labels,count=count)
    attributes = db_attributes.getAttributes(tags=list(attribute_tags))
    attributes_by_tag = attributes.set_index("tag", drop=False).to_dict(orient="index")
    return {"attribute_tags" : attribute_tags, "submission_count" : submission_count_by_attribute_value_tag, "attributes_by_tag" : attributes_by_tag}



@router.get("/user", response_model=AttributeResponseModel)
def get_user_attributes(user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
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
