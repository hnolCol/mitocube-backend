from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import Optional, List
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel

from config.models.genotype import GenotypeModel

from services.users import is_user_admin

from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase





router = APIRouter(
    prefix="/api",
    tags=["Genotypes"]
)



@router.get("/genotypes/q")
def get_genotype_by_query(query : str) -> List[GenotypeModel]:
    """"""
    db_genotype = MCGenotypes.getGenotypeDatabase()
    return db_genotype.find(query=query)



@router.get("/genotypes/{genotype_label}")
def get_genotype_by_label(genotype_label : str):
    """_summary_

    Parameters
    ----------
    genotype_label : str
        _description_
    """
    

@router.get("/genotypes", response_model=List[GenotypeModel])
def get_genotypes(proteome_ids : Optional[str] = None, feature_key : Optional[str] = None):
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
    db_genotype = MCGenotypes.getGenotypeDatabase()
    try:
        if proteome_ids is not None:
            proteome_ids = proteome_ids.split(";")
        genotypes = db_genotype.get(proteome_ids=proteome_ids,feature_key=feature_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return genotypes


@router.post("/genotypes")
def add_genotype(genotype : GenotypeModel):
    """_summary_

    Parameters
    ----------
    genotype : GenotypeModel
        The defined genotype.
    """
    db_genotype = MCGenotypes.getGenotypeDatabase()
    db_genotype.add(genotype=genotype)
    return True 

@router.delete("/genotypes/{genotype_label}")
def delete_genotype_by_label(genotype_label : str): #user : UserModel = Depends(is_user_admin)
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


