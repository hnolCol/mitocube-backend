

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from collections import OrderedDict
from config.models.user import UserModel
from config.models.attributes import AttributeTree
from config.models.conditions_applications import ConditionApplicationAttributeModel, ConditionApplicationStateAttributeModel, ConditionApplicationStateModel, ConditionApplicationTreeModel
from services.random_generators import get_random_string
from config.exceptions.HTTPExceptions import tag_not_found
from services.users import get_user_from_token
from typing import List, Dict, OrderedDict
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


def merge_siblings(nodes):
    """Merge sibling nodes that share the same (type, tag, value),
    pooling their children together. Recurses into children."""
    grouped = OrderedDict()

    for node in nodes:
        key = (node['type'], node['tag'], node.get('value'))
        if key not in grouped:
            new_node = dict(node)      # shallow copy
            new_node['children'] = []  # will fill in below
            grouped[key] = new_node
        grouped[key]['children'].extend(node['children'])

    # recurse so children get merged too, at every depth
    for node in grouped.values():
        node['children'] = merge_siblings(node['children'])

    return list(grouped.values())

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Condition Applications"],
    )

@router.get("/{submission_tag}/ca")
def get_submission_condition_applications(submission_tag: str, attribute_tags : str = None, group_by_attribute : bool = False, group_by_min_state : bool = False, user: UserModel = Depends(get_user_from_token)) -> List[str]|List[ConditionApplicationAttributeModel]|List[ConditionApplicationStateModel]|List[ConditionApplicationStateAttributeModel]:
    "Return the condition applications for a given submission."
    return DB.submissions.get_conditions_applications(submission_tag, attribute_tags=APIParamString(param=attribute_tags).param, group_by_attribute=group_by_attribute, group_by_min_state=group_by_min_state)


@router.get("/{submission_tag}/ca/attributes")
def get_submission_condition_application_attributes(submission_tag: str, include_genotypes : bool = True, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    "Return the condition application attributes for a given submission."
    ca_tags = DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=False)
    attribute_tags = [DB.condition_applications.get_attribute(ca_tag) for ca_tag in ca_tags]
    if include_genotypes and DB.submissions.has_genotypes(tag = submission_tag):
        attribute_tags = ["att_genotype"] + attribute_tags
    return [attr_tag for attr_tag in attribute_tags if attr_tag is not None]



@router.get("/{submission_tag}/samples/ca")
def get_submission_sample_condition_applications(submission_tag: str, attribute_tags : str = None, return_unique: bool = False, include_genotype : bool = True, user: UserModel = Depends(get_user_from_token)) -> List|OrderedDict:
    """Return the condition applications for samples of a given submission.
    Parameters
    ----------
    submission_tag : str
        The tag of the submission to get the condition applications for.
    attribute_tags : str, optional
        If provided, only condition applications with the given attribute tags are returned. By default, None, which means that condition applications of all attributes are returned. Multiple attribute tags can be provided as a
        semicolon-separated string.
    return_unique : bool, optional
        If True, only unique condition application tags are returned. By default, False, which means that a list of sample_tag and the associated ca_tags is returned. If True, a list with unique ca_tags across all samples is returned.
    user : UserModel, optional
        The user to get the condition applications for. By default, the user is extracted from the token.
    Returns
    -------
    List|Dict
        A list of condition application tags for the samples of the submission. If return_unique is False, a list of dictionaries with sample_tag and the associated ca_tags is returned. If return_unique is True, a dictionary with unique ca_tags acrross attribute_tags is returned 
    """
    sample_tags = DB.submissions.get_samples(tag = submission_tag)  #get samples 
    r = []
    genotype_exists = DB.submissions.has_genotypes(tag = submission_tag)
    for sample_tag in sample_tags:
        
        ri = {"tag" : sample_tag}
        ca_tags = DB.samples.get_condition_applications(tag=sample_tag, attribute_tags=APIParamString(param=attribute_tags).param, group_by_attribute=True)  #preload condition applications for samples
        
        if genotype_exists:
            genotype_tags = DB.samples.get_sample_genotype(tag = sample_tag)
            ri["att_genotype"] = genotype_tags
        for ca_tag in ca_tags:
            ri[ca_tag.attribute_tag] = ca_tag.condition_application_tags
        r.append(ri)
        
    df = pd.DataFrame.from_dict(r)
    if return_unique:
        attribute_tags = [col for col in df.columns if col != "tag"] #tag = sample_tag
        r = OrderedDict() 
        for attribute_tag in attribute_tags:
            unique_cas = OrderedDict()

            for ca_tag in df[attribute_tag].str.join(";").values:
                unique_cas[ca_tag] = None

            unique_cas = list(unique_cas.keys())
            r[attribute_tag] = [ca_tag.split(";") for ca_tag in unique_cas]
        return r 
    
    return df.to_dict(orient="records")
    
    
    
@router.get("/{submission_tag}/samples/ca/attributes")
def get_submission_sample_condition_application_attributes(submission_tag: str, include_genotypes : bool = True, user: UserModel = Depends(get_user_from_token)) -> List[str]:
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
    if include_genotypes and DB.submissions.has_genotypes(tag = submission_tag):
        attribute_tags = ["att_genotype"] + attribute_tags
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
    #merge the siblings together - since the ca are stored separately in the database, but they are merged together for the UI. This way we avoid storing the same condition application multiple times in the database, but we can still display them together in the UI.
    return merge_siblings(result) 



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
    if not DB.submissions.exists(tag=submission_tag): raise tag_not_found
    return DB.submissions.edit_condition_applications(
        tag=submission_tag,
        attribute_trees=selected_traits
    )