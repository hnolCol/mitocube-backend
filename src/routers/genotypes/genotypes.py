from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import Optional, List, Dict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.genotype import GenotypeModel, MinimalGenotypeModel

from services.users import is_user_admin, get_user_from_token

from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.database.Database import Database
DB = Database.DB()




router = APIRouter(
    prefix="/api",
    tags=["Genotypes"]
)



@router.get("/genotypes/q")
def get_genotype_by_query(query : str) -> List[MinimalGenotypeModel]:
    """"""
    return DB.genotypes.find(query)


@router.get("/genotypes/{genotype_label}")
def get_genotype_by_label(genotype_label : str):
    """_summary_

    Parameters
    ----------
    genotype_label : str
        _description_
    """
    

@router.get("/genotypes", response_model=List[MinimalGenotypeModel])
def get_genotypes(proteome_ids : Optional[str] = None, feature_tag : Optional[str] = None, user : UserModel = Depends(get_user_from_token)):
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
        proteome_ids=APIParamString(param = proteome_ids).param, 
        protein_tags=APIParamString(param = feature_tag).param
        )
    return r 
    db_genotype = MCGenotypes.getGenotypeDatabase()
    try:
        if proteome_ids is not None:
            proteome_ids = proteome_ids.split(";")
        genotypes = db_genotype.get(proteome_ids=proteome_ids,feature_key=feature_tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return genotypes


@router.post("/genotypes")
def add_genotype(genotype : GenotypeModel, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    genotype : GenotypeModel
        The defined genotype.
    """
    DB.genotypes.add(genotype, user_tag = user.tag)
    
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


