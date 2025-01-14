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
from config.models.attributes import AttributeModel, AttributeValueModel, AttributeResponseModel, AttributeTreeNode, AttributeTraitResponseModel
from config.models.parameter import APIParamString
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from services.submission import map_tags

from lib.data.database.Database import Database
from config.models.unit import UnitTypeResponseModel
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
                   param_name : Literal["allow_for_dataset","mandatory_for_submission","allow_as_filter","allow_for_genotype","allow_for_measurement","allow_for_qc","mandatory_for_active",] = None, 
                   include_traits : bool = True,
                   limit : int = None,
                   user : UserModel = Depends(get_user_from_token)) -> List[AttributeTraitResponseModel]:
    """
    Returns the stored attribute and attribute values.
    """
    if search_string is not None:
        if include_traits:
            return DB.attributes.get_attributes_and_values_by_search_string(search_string=search_string, min_state=min_state, param_name = param_name, limit = limit )
        else:
            return DB.attributes.get_attributes_by_search_string(search_string=search_string, min_state=min_state, param_name = param_name, limit = limit)

    else: 
        attributes = DB.attributes.get(param_name=param_name,min_state=min_state, limit=limit)
        attribute_values = DB.attributes.values(tags = [a.tag for a in attributes])
    return [{"attribute" : attribute, "traits" : DB.attributes.values(tags = [attribute.tag])} for attribute in attributes]
    return AttributeResponseModel(attributes=attributes,
                                  attribute_values=attribute_values)



@router.get("/hierarchy")
def get_attribute_hierarchy(tags : str, submission_tag  : str,  user : UserModel = Depends(get_user_from_token)) -> List[AttributeTreeNode]:
    ""
    attribute_hierarchy = DB.attributes.get_attribute_hierarchy(tags=APIParamString(param=tags).param, submission_tag = submission_tag)
    return attribute_hierarchy



@router.get("/user", response_model=AttributeResponseModel)
def get_user_attributes(user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
    """
    Returns the stored attribute and attribute value definitions that can be used to define a user.
    """
    
    attributes = DB.attributes.get_attributes_for_user()
    attribute_values = DB.attributes.values(tags = [a.tag for a in attributes])

    return AttributeResponseModel(attributes=attributes,
                                  attribute_values=attribute_values)




#change to a more userfull endpoint (pool with datasetattributes )
@router.get("/mandatory")
def get_mandatory_attributes(state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED, user : UserModel = Depends(get_user_from_token)) -> List[AttributeModel]:
    """Returns the mandatory attributes for a submissions. E.g. the attributes that must be 
    defined by the user.


    Parameters
    ----------
    state : SubmissionStatesEnum
        Mandatory attributes for the given state are returned.
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    List[AttributeModel]
        _description_
    """
    return DB.attributes.get_mandatory_attributes(state)



@router.get("/dataset")
def get_dataset_attributes(user : UserModel = Depends(get_user_from_token), min_state : Optional[SubmissionStatesEnums] = None) -> List[AttributeModel]:
    """Returns the dataset attributes (e.g. allow_for_dataset = True)

    Parameters
    ----------
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)
    min_state : Optional[SubmissionStatesEnums], optional
        _description_, by default None

    Returns
    -------
    List[AttributeModel]
        _description_
    """
    return DB.attributes.get_dataset_attributes(min_state=min_state)



@router.get("/values")
def get_attribute_values_by_tag(tag : str) -> List[AttributeValueModel]:
    "Returns the attribute values"
    r = DB.attributes.values(tags = [tag])
    return r 


@router.get("/{attribute_tag}")
def get_attribute_by_tag(attribute_tag : str, user : UserModel = Depends(get_user_from_token)) -> AttributeModel:
    "Returns a single attribute by its tag"     
    attributes = DB.attributes.get(tags=[attribute_tag])
    if len(attributes) == 0:
         raise HTTPException(status_code=404, detail=f"Attribute with the tag {attribute_tag} not found.")
    return attributes[0]


@router.get("/traits/{trait_tag}")
def get_trait(trait_tag : str, include_input : bool = True, submission_tag : str = None) -> AttributeValueModel:
    "Return the specific trait"
    if DB.attributes.exists(value=trait_tag):
        if not include_input: return DB.attributes.get_values(tags=[trait_tag])[0]
        if submission_tag is not None:
            r = DB.attributes.get_values_by_submission_tag(submission_tag=submission_tag, tags=[trait_tag], include_input=include_input)
            ##if there is no input, then return just the trait.
            if len(r) == 0: return DB.attributes.get_values(tags=[trait_tag])[0]
            return DB.attributes.get_values_by_submission_tag(submission_tag=submission_tag, tags=[trait_tag], include_input=include_input)[0]
        else:
            raise HTTPException(status_code=404,detail="Submission tag must be provided if include_input is true.")
        
    raise HTTPException(status_code=404,detail="Tag not associated with a trait/attribute value")



@router.get("/{attribute_tag}/unittypes")
def get_unittypes_by_attribute_tag(attribute_tag : str) -> Dict[str,List[str]]:
    """_summary_

    Parameters
    ----------
    attribute_tag : str
        The attribute's tag to get the unittype for. 

    Returns
    -------
    Dict
        key = attribute_tag
        values = List[unittype_tags] ["concentration"] 


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


# @router.get("/{attribute_tag}/traits/{trait_tag}}")
# def get_trait(attribute_tag : str, trait_tag : str, include_input : bool = True, submission_tag : str = None):
#     "Return the specific trait."
#     if DB.attributes.exists(value=trait_tag):
#         if not include_input: return DB.attributes.get_values(tags=[trait_tag])
#         if submission_tag is not None:
#             return DB.attributes.get_values_by_submission_tag(submission_tag=submission_tag, tags=[trait_tag], include_input=include_input)
#         else:
#             raise HTTPException(status_code=404,detail="Submission tag must be provided if include_input is true.")
        
#     raise HTTPException(status_code=404,detail="Tag not associated with a trait/attribute value")

@router.post("/{attribute_tag}/value")
def add_attribute_value(attribute_tag : str, attribute_value : AttribteValueInsertModel, user : UserModel = Depends(is_user_at_least_curator)) -> None: 
    "Adds an attribute value for an attribute."
    attribute_value_tag = attribute_value.text.replace(" ","_").lower()
    if DB.attributes.exists(tag = attribute_tag, value=attribute_value_tag):
        
        raise HTTPException(status_code=500, detail = "An attribute_value with the same tag exists already.")
    
    DB.attributes.insert_value(attribute_tag, attribute_value=AttributeValueModel(text = attribute_value.text, 
                                                                                  description= attribute_value.description,
                                                                                  attribute_tag = attribute_tag,
                                                                                  tag = attribute_value_tag))
    
    
@router.delete("/{attribute_tag}/values/{trait_tag}")
def delete_attribute_value(attribute_tag : str, trait_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    "Delete a trait for an attribute."
    ok = DB.attributes.delete_value(tag = trait_tag)
    return ok 

@router.patch("/{attribute_tag}/values/{trait_tag}")
def update_attribute_value(attribute_tag : str, 
                           trait_tag : str, 
                           attribute_value_props : dict, 
                           user : UserModel = Depends(is_user_at_least_curator)):
    ""
    "Update a trait for an attribute."
    ok = DB.attributes.update_value(tag = trait_tag, attribute_value_props = attribute_value_props )
    return ok 
    
    
    