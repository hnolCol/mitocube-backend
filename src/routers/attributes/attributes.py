from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Literal
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.annotations.feature import FeatureDataResponseModel, FeatureModel
from config.models.attributes import AttributeModel, AttribteValueInsertModel
from config.enums.states import SubmissionStatesEnums
from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attribute_in_metadata
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.database.ABCDatabase import MCAttributes
from config.models.attributes import AttributeModel, AttributeValueModel, AttributeResponseModel
from config.models.parameter import APIParamString
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from services.submission import map_tags

from lib.data.database.Database import Database

from config.models.prefix import PrefixModel
from config.models.feature import FeatureNeoModel

DB = Database.DB()

router = APIRouter(
    prefix="/api/attributes",
    tags=["Attributes"]
    )
##rather use /q here? 
@router.get("") #AttributeResponseModel
def get_attributes(search_string : Optional[str] = None, 
                   min_state : SubmissionStatesEnums = None, 
                   param_name : Literal["allow_for_dataset","mandatory_for_submission","allow_as_filter","allow_for_genotype","allow_for_measurement","allow_for_qc","mandatory_for_active"] = None, 
                   user : UserModel = Depends(get_user_from_token)) :
    """
    Returns the stored attribute and attribute values.
    """
    if search_string is not None:
        return DB.attributes.get_attributes_and_values_by_search_string(search_string=search_string, min_state=min_state, param_name = param_name )

    else: 
        attributes = DB.attributes.get(param_name=param_name,min_state=min_state)
        attribute_values = DB.attributes.values(tags = [a.tag for a in attributes])
       
    return AttributeResponseModel(attributes=attributes,
                                  attribute_values=attribute_values)



@router.get("/user", response_model=AttributeResponseModel)
def get_user_attributes(user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
    """
    Returns the stored attribute and attribute value definitions that can be assigned to a user.
    """
    
    attributes = DB.attributes.get_attributes_for_user()
    attribute_values = DB.attributes.values(tags = [a.tag for a in attributes])

    return AttributeResponseModel(attributes=attributes,
                                  attribute_values=attribute_values)




#change to a more userfull endpoint (pool with datasetattributes )
@router.get("/mandatory")
def get_mandatory_attributes(user : UserModel = Depends(get_user_from_token)) -> List[AttributeModel]:
    """Returns the mandatory attributes for a submissions. E.g. the attributes that must be 
    defined by the user.

    Parameters
    ----------
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    List[AttributeModel]
        _description_
    """
    return DB.attributes.get_mandatory_attributes()



@router.get("/dataset")
def get_dataset_attributes(user : UserModel = Depends(get_user_from_token), min_state : Optional[SubmissionStatesEnums] = None) -> List[AttributeModel]:
    
    return DB.attributes.get_dataset_attributes(min_state=min_state)



@router.get("/values")
def get_attribute_values_by_tag(tag : str) -> List[AttributeValueModel|FeatureNeoModel]:
    "Returns the attribute values"
    r = DB.attributes.values(tags = [tag])
    
    return r 
    # if len(r) == 0: return r 
    # return r[0][1]


@router.get("/{attribute_tag}")
def get_attribute_by_tag(attribute_tag : str, user : UserModel = Depends(get_user_from_token)) -> AttributeModel:
    "Returns a single attribute by its tag"     
    attributes = DB.attributes.get(tags=[attribute_tag])
    if len(attributes) == 0:
         raise HTTPException(status_code=404, detail=f"Attribute with the tag {attribute_tag} not found.")
    return attributes[0]

@router.get("/traits/{trait_tag}")
def get_attribute_by_tag(trait_tag : str, user : UserModel = Depends(get_user_from_token)) -> AttributeValueModel:
    "Returns a single attribute by its tag"     
    traits = DB.attributes.get_values(tags=[trait_tag])
    if len(traits) == 0:
         raise HTTPException(status_code=404, detail=f"Trait with the tag {traits} not found.")
    return traits[0]






@router.get("/{attribute_tag}/unittypes")
def get_unittypes_by_attribute_tag(attribute_tag : str):
    """_summary_

    Parameters
    ----------
    attribute_tag : str
        The attribute's tag to get the unittype for. 

    Returns
    -------
    _type_


    Raises
    ------
    HTTPException
        _description_
    """
    
    if not DB.unittypes.has_attribute_unit_types(attribute_tag=attribute_tag):
        raise HTTPException(status_code=404, detail="The attribute is not associated with a unittype.")
    
    unit_types = DB.attributes.get_unittype(tags = [attribute_tag])
    return unit_types

@router.get("/units", deprecated=True)
def get_attribute_value_units(tag : str):
    ""     
    r = DB.attributes.unit(tags = APIParamString(param=tag).param)
    if len(r) == 0: return {"units" : [], "prefixes" : PrefixModel()}
    return {"units" : r, "prefixes" : PrefixModel()}




@router.get("/attribute_values/q")
def get_attribute_values(tags : str = None, attribute_value_tag : str = None, attribute_tag : str = None, max_attributes : int = 999999):
    """Returns a list of attribute values that are present in the given submission tags. 
    Use the attribute_value_tag and attribute_tag params to return a subset of attribute_tags. 
    

    Parameters
    ----------
    tags : str, optional
        The submission tag, by default None
    attribute_value_tag : str, optional
        _description_, by default None
    attribute_tag : str, optional
        _description_, by default None
    max_attributes : int, optional
        _description_, by default 999999
        #TODO: implement a limit 

    Returns
    -------
    _type_
        _description_
    """
    
    # db_helper = MCDatabaseHelper.getDatabaseHelper()
    if tags is None:
        tags = DB.get_submission_tags()
    
    attribute_values_by_dataset = DB.attributes.get_attribute_values_by_dataset_tags(
        dataset_tags = APIParamString(param=tags).param,
        attribute_tags = APIParamString(param=attribute_tag).param,
        attribute_value_tags = APIParamString(param=attribute_value_tag).param)
    
    attribute_value_tags = [av.attribute_value.tag for av in attribute_values_by_dataset]
    submission_count_by_attribute_value_tag= dict([(av.attribute_value.tag, {"count" : av.count, "tags" : av.tags}) for av in attribute_values_by_dataset])
    attribute_values_by_tag = dict([(av.attribute_value.tag,av.attribute_value) for av in attribute_values_by_dataset])

    return {"attribute_value_tags" : attribute_value_tags, "count" : submission_count_by_attribute_value_tag, "attribute_values_by_tag" : attribute_values_by_tag}
    
# @router.get("/q")
# def get_attributes(labels : str, count : bool = True, max_attributes : int = 999999):
    
#     db_helper = MCDatabaseHelper.getDatabaseHelper()
#     db_attributes = MCAttributes.getAttributeDatabase() 
#     attribute_tags, submission_count_by_attribute_value_tag = db_helper.get_attribute_tags_by_labels(labels,count=count)
#     attributes = db_attributes.getAttributes(tags=list(attribute_tags))
#     attributes_by_tag = attributes.set_index("tag", drop=False).to_dict(orient="index")
#     return {"attribute_tags" : attribute_tags, "submission_count" : submission_count_by_attribute_value_tag, "attributes_by_tag" : attributes_by_tag}




@router.post("/{attribute_tag}/value")
def add_attribute_value(attribute_tag : str, attribute_value : AttribteValueInsertModel, user : UserModel = Depends(is_user_at_least_curator)): 
    
    attribute_value_tag = attribute_value.text.replace(" ","_").lower()
    if DB.attributes.exists(tag = attribute_tag, value=attribute_value_tag):
        
        raise HTTPException(status_code=500, detail = "An attribute_value with the same tag exists already.")
    
    DB.attributes.insert_value(attribute_tag, attribute_value=AttributeValueModel(text = attribute_value.text, 
                                                                                  description= attribute_value.description,
                                                                                  attribute_tag = attribute_tag,
                                                                                  tag = attribute_value_tag))
    
    
@router.delete("/{attribute_tag}/values/{attribute_value_tag}")
def delete_attribute_value(attribute_tag : str, attribute_value_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    
    ok = DB.attributes.delete_value(tag = attribute_value_tag)
    

@router.patch("/{attribute_tag}/values/{attribute_value_tag}")
def update_attribute_value(attribute_tag : str, 
                           attribute_value_tag : str, 
                           attribute_value_props : dict, 
                           user : UserModel = Depends(is_user_at_least_curator)):
    ""
    ok = DB.attributes.update_value(tag = attribute_value_tag, attribute_value_props = attribute_value_props )
    
    
    
    