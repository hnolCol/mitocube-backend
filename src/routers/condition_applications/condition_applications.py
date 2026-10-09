from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
import pandas as pd 
import numpy as np 
from typing import List, Dict, OrderedDict, defaultdict

from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationTreeResponseModel, ConditionApplicationTreeModel

from services.users import get_user_from_token
from services.submission import check_submission_access

from services.condition_application import build_condition_application_tree
from config.models.parameter import APIParamString


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/condition_applications",
    tags=["Condition Applications"]
    )


@router.get("/q")
def query_condition_applications(search_string : str = None, 
                                 samples_only : bool = True, 
                                 protein_tags : str = None, 
                                 submission_tag : str = None, 
                                 attribute_tag : str = None, 
                                 trait_tag : str = None, 
                                 sort_by_frequency : bool = True, 
                                 limit : int = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    """Query condition applications based on different criteria.
    
    Parameters
    ----------
    samples_only : bool, optional
        If True, only return condition applications that are associated with samples, by default True
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

    if submission_tag is not None:
        check_submission_access(submission_tag = submission_tag, user = user, db = db)
    ca_tags = db.condition_applications.find(search_string = search_string, samples_only = samples_only, protein_tags = protein_tags, submission_tag = submission_tag, attribute_tag = attribute_tag, trait_tag = trait_tag, sort_by_frequency = sort_by_frequency, limit = limit)

    return ca_tags

@router.get("/q/hierarchy")
def ca_hierarchy(search_string: str, limit: int = None, exclude_attribute_group: str = None, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    
    ca_tags_with_protein_value = []
    protein_tags = db.proteins.find(search_string=search_string, is_condition_value=True)
    
    
    exclude_list = APIParamString(param=exclude_attribute_group).param
    
    if len(protein_tags) > 0:
        ca_tags_with_protein_value = db.condition_applications.find(protein_tags=protein_tags, 
                                                                    sort_by_frequency=True,
                                                                    exclude_attribute_group=exclude_list,
                                                                    limit = limit
                                                                )
    
    ca_tags_by_search_string = db.condition_applications.find( search_string=search_string, 
                                                                samples_only=False, 
                                                                sort_by_frequency=True,
                                                                exclude_attribute_group=exclude_list,
                                                                limit = limit
                                                            )
    
    ca_tags = ca_tags_with_protein_value + [ca_tag for ca_tag in ca_tags_by_search_string if ca_tag not in ca_tags_with_protein_value]
    tree = defaultdict(lambda: defaultdict(list))

    for ca in ca_tags:
        attr = db.condition_applications.get_attribute(ca)  # ideally pre-fetched
        trait = db.condition_applications.get_trait(ca)

        tree[attr][trait].append(ca)
    
    result = [
        {
            "type": "attribute",
            "tag": attr,
            "children": [
                {
                    "type": "trait",
                    "tag": trait,
                    "children": ca_list
                }
                for trait, ca_list in traits.items()
            ]
        }
        for attr, traits in tree.items()
    ]
    return result

        
        
            
            
    
    
    
 
@router.get("/{ca_tag}")
def get_ca_by_tag(ca_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[ConditionApplicationTreeResponseModel]:
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
    if not db.condition_applications.exists(tag = ca_tag): raise HTTPException(status_code=404, detail=f"No condition application found for tag {ca_tag}")
    ca = db.condition_applications.get(tag = ca_tag)

    return build_condition_application_tree(ca)


 
@router.get("/{ca_tag}/value_exists")
def get_ca_by_tag(ca_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """Returns if the condition application has a condition value. 

    Parameters
    ----------
    ca_tag : str
        The tag associated with the condition application w

    Returns
    -------
    bool
        Condition Value exists for the condition application or not.
        
    """
    if not db.condition_applications.exists(tag = ca_tag): return False
    return db.condition_applications.has_value(tag = ca_tag)

@router.get("/{ca_tag}/text")
def get_ca_name_by_tag(ca_tag : str, handle_genotypes : bool = True, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> str:
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
    if handle_genotypes and db.genotypes.exists(tag = ca_tag):
        return db.genotypes.get_text(tag = ca_tag)
    if not db.condition_applications.exists(tag = ca_tag): raise HTTPException(status_code=404, detail=f"No condition application found for tag {ca_tag}")
    return db.condition_applications.get_text(tag = ca_tag)    


@router.get("/{tag}/tree_for_ui")
def get_tree_for_ui(ca_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> Dict:
    """
    Returns the condition application tree transformed for UI display.
    """
    ca = db.condition_applications.get_tree(tag= ca_tag)
    ui_tree = db.condition_applications.transform_for_ui(ca)
    return [ui_tree]
