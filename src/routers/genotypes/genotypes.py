from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import Optional, List, Dict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.genotype import GenotypeModel, MinimalGenotypeModel, InsertGeneticApplicationModel

from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator


from lib.database.Database import Database
DB = Database.DB()


genotype_not_found = HTTPException(status_code=404, detail="Genotype not associated with tag.")

router = APIRouter(
    prefix="/api",
    tags=["Genotypes"]
)


@router.get("/genotypes/{genotype_tag}/proteins")
def get_genotype_proteins(genotype_tag: str, user: UserModel = Depends(get_user_from_token)):
    """ 
    Get the proteins of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    genotype = DB.genotypes.get_proteins(tag = genotype_tag)

    return genotype

@router.get("/genotypes/{genotype_tag}/item")
def get_genotype_item(genotype_tag: str, user: UserModel = Depends(get_user_from_token)):
    """ 
    Get the item of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    genotype = DB.genotypes.get_item(tag = genotype_tag)

    return genotype

@router.get("/genotypes/{genotype_tag}/description")
def get_genotype_description(genotype_tag: str, user: UserModel = Depends(get_user_from_token)):
    """ 
    Get the description of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise 
    genotype = DB.genotypes.get_description(tag = genotype_tag)

    return genotype

@router.get("/genotypes/{genotype_tag}/text")
def get_genotype_text(genotype_tag: str, user: UserModel = Depends(get_user_from_token)):
    """ 
    Get the full text information of a genotype by its tag. 
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    genotype = DB.genotypes.get_text(tag = genotype_tag)

    return genotype

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
    print(genotype)
    


    ok = DB.genotypes.insert(genotype, user_tag = user.tag)
    if not ok:
        raise HTTPException(status_code=400, detail="Genotype already exists in the database.")

    return True 

@router.delete("/genotypes/{genotype_label}")
def delete_genotype_by_label(genotype_label : str, user : UserModel = Depends(is_user_admin)): #
    """_summary_

    Parameters
    ----------
    genotype_label : str
        _description_

    Returns
    -------
    bool
        If the deletion was successful. If genotype_label is unknown, false is returned otherwise true.
    """
    try:
        db_genotype = MCGenotypes.getGenotypeDatabase()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return db_genotype.delete(label=genotype_label)

@router.get("/genotypes/{genotype_tag}/relationships/count")
def get_genotype_relationship_count(genotype_tag: str,user: UserModel = Depends(get_user_from_token)):
    """
    Count how many relationships (e.g., samples) are linked to the given genotype.
    """

    if not DB.genotypes.exists(tag=genotype_tag): raise genotype_not_found
    count = DB.genotypes.count(tag=genotype_tag)

    return count

@router.delete("/genotype/{genotype_tag}")
def delete_genotype(genotype_tag: str, user: UserModel = Depends(is_user_at_least_curator)):
    """
    Delete a genotype by its tag.
    """
    deleted = DB.genotypes.delete(genotype_tag)

    if not deleted:
        raise genotype_not_found
    
    return {f"Genotype '{genotype_tag}' deleted."}