from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Literal
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.attributes import AttributeModel, AttribteValueInsertModel, InsertTraitModel, UpdateTraitModel
from config.enums.states import SubmissionStatesEnums

from services.users import get_user_from_token, is_user_at_least_curator


from config.models.attributes import AttributeModel, AttributeResponseModel, AttributeValueModel, AttributeTreeNode, AttributeTraitResponseModel, AttributeTraitTagResponseModel, TraitResponseModel, AttributeInsertModel
from config.models.parameter import APIParamString

from lib.database.Database import Database

DB = Database.DB()

router = APIRouter(
    prefix="/api/attributes",
    tags=["Attributes"]
    )



@router.post("")
def insert_attribute(attribute : AttributeInsertModel, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    "Inserts a new attribute into the database. Returns True if successful, False otherwise."
    attribute_tag = "att_" + attribute.text.replace(" ","_").lower().encode('utf-8', 'ignore').decode('utf-8')
    if DB.attributes.exists(tag = attribute_tag):
        raise HTTPException(status_code=500, detail = "An attribute with the same tag exists already. Alter the text and check if the attribute is not already present before proceeding.")
    if len(attribute_tag) > 35:
        raise HTTPException(status_code=500, detail = "The attribute tag is too long. Please use a shorter text for the attribute.")
    if len(attribute_tag) <= 4:
        raise HTTPException(status_code=500, detail = "The attribute tag is too short. Please use a longer text for the attribute. Note that the attribute tag is generated from the text by replacing spaces with underscores and adding the prefix 'att_'. Non utf-8 characters are removed. The attribute tag must be at least 5 characters long.")
    
    ok = DB.attributes.insert(tag=attribute_tag, 
                              text=attribute.text, 
                              priority=attribute.priority, 
                              min_state=attribute.min_state, 
                              abbreviation=attribute.abbr, 
                              allow_input=attribute.allow_input, 
                              group_tags=attribute.group_tags, 
                              children=attribute.children, 
                              required_trait_tags=attribute.required_trait_tags)
    return ok


@router.get("/q")
def get_attributes(
    search_string: Optional[str] = None,
    min_state: SubmissionStatesEnums = None,
    attribute_groups: Optional[str] = None,  # Accept any string, handle parsing below
    include_traits: bool = True,
    limit: int = 20,
    group_by : Optional[Literal["attribute_group","min_state"]] = None,
    user: UserModel = Depends(get_user_from_token)
) -> List[AttributeTraitTagResponseModel] | List[str] | Dict[str, List[str]]:
    """
    Returns the stored attribute and traits.
    Allows multiple attribute groups separated by ';'.
    """

    if attribute_groups is not None:
        attribute_groups = APIParamString(param = attribute_groups).param
        
    if include_traits:
            return DB.attributes.find_attributes_and_traits(
                search_string=search_string,
                min_state=min_state,
                limit=limit,
                attribute_groups=attribute_groups
            )
        
    if search_string is not None and isinstance(search_string, str) and len(search_string) > 0:
        
            return DB.attributes.find_attribute(
                search_string,
                attribute_groups=attribute_groups,
                limit=limit,
                min_state=min_state,
                group_by=group_by
            )
    #return all attributes 
    return DB.attributes.get(
        limit=limit,
        attribute_groups=attribute_groups,
        min_state=min_state,
        group_by=group_by
    )


@router.get("/hierarchy")
def get_attribute_hierarchy(tags : str, submission_tag  : str,  user : UserModel = Depends(get_user_from_token)) -> List[AttributeTreeNode]:
    ""
    attribute_hierarchy = DB.attributes.get_attribute_hierarchy(tags=APIParamString(param=tags).param, submission_tag = submission_tag)
    return attribute_hierarchy

@router.get("/groups", summary="Returns the attribute group tags present in the database.")
def get_attribute_groups(limit : int = None) -> List[str]:
    """
    Returns the attribute group tags present in the database.
    """
    return DB.attributes.get_attribute_group_tags(limit=limit)





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


@router.get("/count", summary="Returns the number of attributes in the database.")
def get_attribute_count(user : UserModel = Depends(get_user_from_token)) -> int:
    """Returns the number of attributes in the database.

    Parameters
    ----------
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    int
        The number of attributes in the database.
    """
    return DB.attributes.count()

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


@router.get("/groups/{group_tag}")
def get_attribute_tags_by_group(group_tag : str, min_state : SubmissionStatesEnums = None, limit : int = None) -> List[str]:
    """Returns the attribute tags associated with a specific group."""
    return DB.attributes.find_attribute(attribute_groups=APIParamString(param=group_tag).param, min_state = min_state, limit=limit)


@router.get("/{attribute_tag}")
def get_attribute_by_tag(attribute_tag : str, user : UserModel = Depends(get_user_from_token)) -> AttributeResponseModel:
    "Returns a single attribute by its tag"     
    attribute = DB.attributes.attribute(tag=attribute_tag)
    return attribute


@router.get("/{attribute_tag}/abbr")
def get_attribute_abbr(attribute_tag : str, user : UserModel = Depends(get_user_from_token)) -> str:
    "Returns the abbreviation of a single attribute by its tag"     
    attribute_abbr = DB.attributes.get_abbr(tag=attribute_tag)
    if isinstance(attribute_abbr, str) and len(attribute_abbr) > 0:
        return attribute_abbr
    return ""

@router.get("/{attribute_tag}/required_traits")
def get_attribute_required_traits(attribute_tag : str) -> List[str]:
    "Returns the list of required traits for an attribute by its tag"
    return DB.attributes.get_required_traits(tag=attribute_tag)

@router.get("/traits/q")
def query_trait(search_string : str, attribute_tag : str = None, limit : int = 50) -> List[str]:
    "Queries the trait database and returns the tags that match the search string."
    if search_string == "": return DB.attributes.get_trait_tags(tag = attribute_tag, limit=limit) 
    return DB.attributes.find_trait(search_string=search_string, attribute_tag=attribute_tag, limit=limit)



@router.get("/traits/{trait_tag}")
def get_trait(trait_tag : str, include_input : bool = False, submission_tag : str = None) -> TraitResponseModel:
    "Return the specific trait"
    if DB.attributes.exists(trait=trait_tag):
        if not include_input: return DB.attributes.trait(trait_tag = trait_tag)
        if submission_tag is not None:
            r = DB.attributes.get_values_by_submission_tag(submission_tag=submission_tag, tags=[trait_tag], include_input=include_input)
            ##if there is no input, then return just the trait.
            if len(r) == 0: return DB.attributes.get_values(tags=[trait_tag])[0]
            return DB.attributes.get_values_by_submission_tag(submission_tag=submission_tag, tags=[trait_tag], include_input=include_input)[0]
        else:
            raise HTTPException(status_code=404,detail="Submission tag must be provided if include_input is true.")
        
    raise HTTPException(status_code=404,detail="Tag not associated with a trait/attribute value")

@router.get("/traits/{trait_tag}/text")
def get_trait_text(trait_tag : str) -> str:
    "Returns the text associated with a trait tag"
    if not DB.attributes.exists(trait=trait_tag):
        raise HTTPException(status_code=404, detail="Trait not found")
    trait_text = DB.attributes.get_trait_text(tag = trait_tag)
    if trait_text is None:
        raise HTTPException(status_code=404, detail="Trait text not found")
    return trait_text


@router.get("/{attribute_tag}/traits") 
def get_all_traits_for_attribute_tag(attribute_tag : str, limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns all trait tags associated with an attribute"
    if not DB.attributes.exists(tag = attribute_tag): 
        raise HTTPException(status_code=404,detail="Tag not associated with an attribute")
    
    return DB.attributes.get_trait_tags(tag = attribute_tag, limit=limit)

@router.get("/{attribute_tag}/traits/count") 
def get_all_traits_count_for_attribute_tag(attribute_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "Returns the count of all trait tags associated with an attribute"
    if not DB.attributes.exists(tag = attribute_tag): 
        raise HTTPException(status_code=404,detail="Tag not associated with an attribute")

    return DB.attributes.count_traits(tag = attribute_tag)

    return DB.attributes.get_trait_tags(tag = attribute_tag)


@router.get("/{attribute_tag}/children")
def get_attribute_children(attribute_tag : str) -> List[str]:
    "Returns the list of children of an attribute by its tag"
    
    if not DB.attributes.exists(tag = attribute_tag): 
        raise HTTPException(status_code=404,detail="Tag not associated with a trait/attribute value")
    
    return DB.attributes.get_children(tag = attribute_tag)



@router.get("/{attribute_tag}/min_state")
def get_min_state_for_attribute(attribute_tag : str) -> SubmissionStatesEnums:
    """Returns the minimum state for an attribute.

    Parameters
    ----------
    attribute_tag : str
        The tag of the attribute.

    Returns
    -------
    SubmissionStatesEnums
        The minimum state for the attribute.
    """
    
    if not DB.attributes.exists(tag = attribute_tag): 
        raise HTTPException(status_code=404,detail="Tag not associated with an attribute")
    
    return DB.attributes.get_min_state(tag = attribute_tag)


@router.get("/{attribute_tag}/priority")
def get_priority_for_attribute(attribute_tag : str) -> int:
    """Returns the priority for an attribute.

    Parameters
    ----------
    attribute_tag : str
        The tag of the attribute.

    Returns
    -------
    int
        The priority for the attribute.
    """
    
    if not DB.attributes.exists(tag = attribute_tag): 
        raise HTTPException(status_code=404,detail="Tag not associated with an attribute")

    return DB.attributes.get_priority(tag = attribute_tag)


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
    "Deletes a trait for an attribute."
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
    
    
@router.post("/{attribute_tag}/traits")
def add_trait_to_attribute( attribute_tag: str, trait: InsertTraitModel, user: UserModel = Depends(get_user_from_token),):
    "Adds a trait to an attribute."
    
    trait = InsertTraitModel( attribute_tag=attribute_tag,
                              value=trait.value,
                              text=trait.text,
                              description=trait.description,
                              priority=trait.priority,
                            )

    if DB.attributes.exists(tag=attribute_tag, trait=trait.tag):
        raise HTTPException(
            status_code=409,
            detail="A trait with the same tag exists already for this attribute.",
        )

    DB.attributes.insert_trait(trait=trait)
    return {"tag": trait.tag}

@router.patch("/{attribute_tag}/traits/{trait_tag}")
def update_trait (attribute_tag: str, trait_tag: str, updates: UpdateTraitModel, user: UserModel = Depends(is_user_at_least_curator)):
    "Updates a trait's text, description, and/or priority."
    if not DB.attributes.exists(tag=attribute_tag, trait=trait_tag):
        raise HTTPException(
            status_code=404,
            detail="Trait not found for this attribute.",
        )

    DB.attributes.update_trait(trait_tag=trait_tag, trait=updates)
    return {"tag": trait_tag}


@router.delete("/{attribute_tag}/traits/{trait_tag}")
def delete_trait( attribute_tag: str, trait_tag: str, user: UserModel = Depends(is_user_at_least_curator)):
    "Deletes a trait if it is not connected to any ConditionApplication."
    try:
        DB.attributes.delete_trait(trait_tag=trait_tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"tag": trait_tag, "deleted": True}