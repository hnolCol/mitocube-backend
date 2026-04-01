

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.attributes import AttributeTree
from config.models.conditions_applications import ConditionApplicationAttributeModel, ConditionApplicationTreeModel
from services.random_generators import get_random_string
from config.exceptions.HTTPExceptions import tag_not_found
from services.users import get_user_from_token
from typing import List, Dict
import pandas as pd

from config.models.parameter import APIParamString 

def transform_for_ui(item : ConditionApplicationTreeModel, r : List = None, ca_id : str = None) -> List[Dict]:


    return {"type" : "attribute",
        "id" : ca_id,
        "tag" : item.attribute_tag,
        "children" : [
            {
                "type" : "trait",
                "tag" : item.trait_tag,
                "value" : item.value,
                "id" : ca_id,
                "children" : [transform_for_ui(item = child, ca_id=ca_id) for child in item.children]
            }
        ]
    }


DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Condition Applications"],
    )

@router.get("/{submission_tag}/ca")
def get_submission_condition_applications(submission_tag: str, group_by_attribute : bool = False, user: UserModel = Depends(get_user_from_token)) -> List[str]|List[ConditionApplicationAttributeModel]:
    "Return the condition applications for a given submission."
    return DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=group_by_attribute)


@router.get("/{submission_tag}/ca/attributes")
def get_submission_condition_application_attributes(submission_tag: str, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    "Return the condition application attributes for a given submission."
    ca_tags = DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=False)
    attribute_tags = [DB.condition_applications.get_attribute(ca_tag) for ca_tag in ca_tags]
    return [attr_tag for attr_tag in attribute_tags if attr_tag is not None]



@router.get("/{submission_tag}/samples/ca")
def get_submission_sample_condition_applications(submission_tag: str, attribute_tags : str = None, user: UserModel = Depends(get_user_from_token)) -> List:

    sample_tags = DB.submissions.get_samples(tag = submission_tag)  #get samples 
    r = []
    
    for sample_tag in sample_tags:
        
        ri = {"tag" : sample_tag}
        ca_tags = DB.samples.get_condition_applications(tag=sample_tag, attribute_tags=APIParamString(param=attribute_tags).param, group_by_attribute=True)  #preload condition applications for samples
        for ca_tag in ca_tags:
            ri[ca_tag.attribute_tag] = ca_tag.condition_application_tags
        r.append(ri)
        
    df = pd.DataFrame.from_dict(r)
    return df.to_dict(orient="records")
    
    
    
@router.get("/{submission_tag}/samples/ca/attributes")
def get_submission_sample_condition_application_attributes(submission_tag: str, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    "Return the condition application attributes for samples of a given submission."
    if not DB.submissions.exists(tag = submission_tag):
        return tag_not_found
    ca_tags = DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=False)
    sample_tags = DB.submissions.get_samples(tag = submission_tag)  #ensure samples are loaded
    if len(sample_tags) == 0:
        raise HTTPException(status_code=404, detail="No samples found for this submission.")
    attribute_tags = []
    for sample_tag in sample_tags:
        ca_tags = DB.samples.get_condition_applications(tag=sample_tag, group_by_attribute=False)
        attribute_tags.extend([DB.condition_applications.get_attribute(ca_tag) for ca_tag in ca_tags])

    return pd.Series(attribute_tags).dropna().unique().tolist()


@router.get("/{submission_tag}/ca/data")
def get_ca_tree_for_submission(submission_tag: str, user: UserModel = Depends(get_user_from_token)) -> List:
    """
    Get the condition application tree data for a given submission.
    """
    if not DB.submissions.exists(tag=submission_tag): raise tag_not_found
    ca_tags = DB.submissions.get_conditions_applications(tag=submission_tag)

    result = []
    for ca_tag in ca_tags:
        tree = DB.condition_applications.get_tree(tag=ca_tag)
        if tree:
            result.append(transform_for_ui(tree[0], ca_id=submission_tag))
    return result



# @router.post("/{submission_tag}/ca/update")
# def update_submission_condition_applications( submission_tag: str, selected_traits: List[AttributeTree],  user: UserModel = Depends(get_user_from_token)
# ) -> bool:
#     if not DB.submissions.exists(tag=submission_tag): raise tag_not_found
#     return DB.submissions.edit_condition_application(
#         tag=submission_tag,
#         attribute_trees=selected_traits
#     )


@router.post("/{submission_tag}/ca/update")
def update_submission_condition_applications(
    submission_tag: str,
    selected_traits: List[AttributeTree],
    user: UserModel = Depends(get_user_from_token)
) -> bool:
    print("RECEIVED:", selected_traits)
    if not DB.submissions.exists(tag=submission_tag): raise tag_not_found
    return DB.submissions.edit_condition_applications(
        tag=submission_tag,
        attribute_trees=selected_traits
    )