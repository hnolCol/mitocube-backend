from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import Optional, List, Dict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.genotype import GenotypeModel, MinimalGenotypeModel, InsertGeneticApplicationModel, GeneModificationModel
from config.models.conditions_applications import ConditionApplicationTreeModel
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator

from services.random_generators import get_random_string
from lib.database.Database import Database
DB = Database.DB()


    
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
    



genotype_not_found = HTTPException(status_code=404, detail="Genotype not associated with tag.")

router = APIRouter(
    prefix="/api",
    tags=["Genotypes"]
)

@router.get("/genotypes/{genotype_tag}/proteome")
def get_genotype_proteome(genotype_tag: str, user: UserModel = Depends(get_user_from_token)) -> Optional[str]:
    """ 
    Get the proteome of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    proteome_tag = DB.genotypes.get_proteome(tag = genotype_tag)

    return proteome_tag 

@router.get("/genotypes/{genotype_tag}/exists")
def check_genotype_exists(genotype_tag: str, user: UserModel = Depends(get_user_from_token)) -> bool:
    """ 
    Check if a genotype exists by its tag. 
    """

    exists = DB.genotypes.exists(tag = genotype_tag)

    return exists


@router.get("/genotypes/{genotype_tag}/proteins")
def get_genotype_proteins(genotype_tag: str, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """ 
    Get the proteins of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    protein_tags = DB.genotypes.get_proteins(tag = genotype_tag)

    return protein_tags

@router.get("/genotypes/{genotype_tag}/item")
def get_genotype_item(genotype_tag: str, user: UserModel = Depends(get_user_from_token)):
    """ 
    Get the item of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    genotype = DB.genotypes.get_item(tag = genotype_tag)

    return genotype

@router.get("/genotypes/{genotype_tag}/description")
def get_genotype_description(genotype_tag: str, user: UserModel = Depends(get_user_from_token)) -> str:
    """ 
    Get the description of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    genotype_description = DB.genotypes.get_description(tag = genotype_tag)

    return genotype_description

@router.get("/genotypes/{genotype_tag}/text") 
def get_genotype_text(genotype_tag: str, user: UserModel = Depends(get_user_from_token)) -> str:
    """ 
    Get the full text information of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    genotype_text = DB.genotypes.get_text(tag = genotype_tag)

    return genotype_text

@router.get("/genotypes/q")
def get_genotype_by_query(search_string : str = None, user_tag : str = None, limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    """
    Finds genotype tags that match the search string.
    Parameters
    ----------
    search_string : str, optional
        The search string to look for in the genotype tags., by default None
    user_tag : str, optional
        If provided, only genotypes created by the given user_tag are returned., by default None
    limit : int, optional
        The maximum number of genotype tags to return., by default None
    """
    return DB.genotypes.find(search_string=search_string, user_tag=user_tag, limit=limit)


@router.get("/genotypes/{genotype_tag}")
def get_genotype_by_label(genotype_tag : str):
    """_summary_

    Parameters
    ----------
    genotype_label : str
        _description_
    """
    

@router.get("/genotypes", response_model=List[MinimalGenotypeModel])
def get_genotypes(proteome_tags : Optional[str] = None, feature_tag : Optional[str] = None, user : UserModel = Depends(get_user_from_token)):
    """Returns the genotypes defined using the params: ``proteome_id`` or ``feature_key``. 
    If feature_key is provided, the proteome_id is ingored. If ``proteome_id`` is given, then
    all genotypes that are defined for a given proteome_id is provided. 

    Parameters
    ----------
    proteome_ids : Optional[str], optional
        Multiple proteome ids should be provided by using ';' as a separator., by default None
    feature_key : Optional[str], optional
        The feature key can be used to access genotypes that affect a certain feature_key, by default Optional[str]=None
    """
    r = DB.genotypes.get(
        proteome_tags=APIParamString(param = proteome_tags).param, 
        protein_tags=APIParamString(param = feature_tag).param
        )
    return r 


@router.post("/genotypes")
def insert_genotype(genotype : InsertGeneticApplicationModel, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    genotype : GenotypeModel
        The defined genotype.
    """
    
    ok = DB.genotypes.insert(genotype, user_tag = user.tag)
    if not ok:
        raise HTTPException(status_code=400, detail="Genotype already exists in the database or another error occurred.")

    return True 

@router.put("/genotypes/{tag}")
def edit_genotype(tag: str, genotype: InsertGeneticApplicationModel, user: UserModel = Depends(get_user_from_token)):
    """
    Parameters
    ----------
    tag : str
        The genotype tag.
    genotype : InsertGeneticApplicationModel
        The updated genotype data.
    """
    edit = DB.genotypes.edit(tag = tag, data = genotype, user_tag = user.tag)

    if not edit:
        raise HTTPException(status_code=400, detail="Failed to update genotype.")

    return edit

@router.get("/genotypes/{genotype_tag}/samples/count")
def get_genotype_relationship_count(genotype_tag: str,user: UserModel = Depends(get_user_from_token)):
    """
    Count how many relationships (e.g., samples) are linked to the given genotype.
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    count = DB.samples.count(genotype_tag=genotype_tag)

    return count


@router.get("/genotypes/{genotype_tag}/condition_applications/data")
def get_ca_tree_for_genotype(genotype_tag : str, user : UserModel = Depends(get_user_from_token)) -> List:
    """
    Get the condition application tree data for a given genotype.
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    ca_tags = DB.genotypes.get_condition_applications(tag = genotype_tag)
    print([transform_for_ui(DB.condition_applications.get_tree(tag=ca_tag)[0], ca_id=get_random_string(4)) for ca_tag in ca_tags])
    return [transform_for_ui(DB.condition_applications.get_tree(tag=ca_tag)[0], ca_id=get_random_string(4)) for ca_tag in ca_tags]

@router.delete("/genotypes/{genotype_tag}", response_model=bool)
def delete_genotype(genotype_tag: str,  user : UserModel = Depends(is_user_admin)) -> bool:
    """
    Delete a genotype by its tag.
    """
    # deleted = DB.genotypes.delete(genotype_tag)

    # if not deleted:
    #     raise genotype_not_found
    
    # return {f"Genotype '{genotype_tag}' deleted."}

    if not DB.genotypes.exists(tag=genotype_tag):
        raise HTTPException(status_code=404, detail="Genotype not found.")
    
    print(f"Deleting genotype with tag: {genotype_tag}")
    ok = DB.genotypes.delete(tag = genotype_tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete genotype from the database.")
    return ok

@router.get("/genotypes/{genotype_tag}/condition_applications")
def genotype_condition_applications(genotype_tag: str, user: UserModel = Depends(get_user_from_token)):

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found

    ca = DB.genotypes.get_condition_applications(tag=genotype_tag)
    return ca

@router.get("/genotypes/{tag}/condition_applications/data")
def genotype_condition_applications_data(tag: str, user: UserModel = Depends(get_user_from_token)):

    if not DB.genotypes.exists(tag=tag): raise genotype_not_found

    data = DB.genotypes.get_condition_application_data(tag=tag)
    return data

