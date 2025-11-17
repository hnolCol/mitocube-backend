from fastapi import APIRouter, Depends, HTTPException
import pandas as pd 
import numpy as np 
from typing import List, Dict 

from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationTreeResponseModel
from lib.database.Database import Database

from services.users import get_user_from_token

from services.condition_application import build_condition_application_tree

DB = Database.DB()


router = APIRouter(
    prefix="/api/condition_applications",
    tags=["Condition Applications"]
    )

def extract_ca_item(item, add_separator = False) -> str:
    """Extracts the text representation of a condition application item recursively.
    Parameters
    ----------
    item : Dict
        The condition application item. The keys must include 'value', 'trait_tag', 'attribute_tag', and 'children'.
        If no children are present, 'children' should be an empty list.
    add_separator : bool, optional
        Whether to add a separator after the item, by default False
    """
    t = ""
    if item['value'] is not None:
            val = item['value']
            if isinstance(val, float):
                # Use general format, strip trailing .0, use scientific notation for small numbers
                t += f"{val:.6g}"
            else:
                t += f"{val}"
    t += f"{DB.attributes.get_trait_text(item['trait_tag'])}"
    if item["children"] is not None and len(item["children"]) > 0:
        t += " ("
        for n,c in enumerate(item["children"]):
            t += extract_ca_item(c, add_separator = n < len(item["children"])-1) 
            t += ", " if add_separator else ""
        t += ")"
    return t

@router.get("/q")
def query_condition_applications(samples_only : bool = True, submission_tag : str = None, attribute_tag : str = None, trait_tag : str = None, sort_by_frequency : bool = True, limit : int = None, user : UserModel = Depends(get_user_from_token)):
    """Query condition applications based on different criteria.
    
    Parameters
    ----------
    samples_only : bool, optional
        If True, only return condition applications that are associated with samples, by default False
    trait_tag : str, optional
        If provided, only return condition applications that are associated with the given trait tag, by default None
    attribute_tag : str, optional
        If provided, only return condition applications that are associated with the given attribute tag, by default None
    submission_tag : str, optional
        If provided, only return condition applications that are associated with the given submission tag, by default   None
    sort_by_frequency : bool, optional
        If True, sort the results by the most frequent condition applications, by default True
    limit : int, optional
        If provided, limit the number of results returned, by default None

   
    Returns
    -------
    List[ConditionApplicationTreeResponseModel]
        A list of condition applications matching the query criteria.
        
    """

    ca_tags = DB.condition_applications.find(samples_only = samples_only, submission_tag = submission_tag, attribute_tag = attribute_tag, trait_tag = trait_tag, sort_by_frequency = sort_by_frequency, limit = limit)

    return ca_tags


@router.get("/{ca_tag}")
def get_ca_by_tag(ca_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[ConditionApplicationTreeResponseModel]:
    """Returns the condition application by its tag. 

    Parameters
    ----------
    ca_tag : str
        The tag associated with the condition application w

    Returns
    -------
    ConditionApplicationAttributeModel
        The condition application as a pydantic model
        
    """
    if not DB.condition_applications.exists(tag = ca_tag): raise HTTPException(status_code=404, detail=f"No condition application found for tag {ca_tag}")
    ca = DB.condition_applications.get(tag = ca_tag)

    return build_condition_application_tree(ca)




@router.get("/{ca_tag}/text")
def get_ca_name_by_tag(ca_tag : str, user : UserModel = Depends(get_user_from_token)) -> str:
    """Returns the text representation of the condition application by its tag. 

    Parameters
    ----------
    ca_tag : str
        The tag associated with the condition application

    Returns
    -------
    str
        The text representation of the condition application.
        
    """
    
    if not DB.condition_applications.exists(tag = ca_tag): raise HTTPException(status_code=404, detail=f"No condition application found for tag {ca_tag}")
    ca_tree = DB.condition_applications.get_tree(tag = ca_tag)



    t = ""
    for c in ca_tree: 
        t+= extract_ca_item(c)
    return t


@router.get("/{tag}/tree_for_ui")
def get_tree_for_ui(ca_tag : str, user : UserModel = Depends(get_user_from_token)) -> Dict:
    """
    Returns the condition application tree transformed for UI display.
    """
    ca = DB.condition_applications.get_tree(tag= ca_tag)
    ui_tree = DB.condition_applications.transform_for_ui(ca)
    return [ui_tree]
