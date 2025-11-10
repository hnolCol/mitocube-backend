from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import Optional, List, Dict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.genotype import GenotypeModel, MinimalGenotypeModel, InsertGeneticApplicationModel

from services.users import is_user_admin, get_user_from_token


from lib.database.Database import Database
DB = Database.DB()




router = APIRouter(
    prefix="/api",
    tags=["Genotypes"]
)



@router.get("/genotypes/q")
def get_genotype_by_query(search_string : str = None) -> List[str]:
    """"""
    return DB.genotypes.find(search_string=search_string)


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


