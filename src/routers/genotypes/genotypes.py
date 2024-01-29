from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import Optional, List
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel

from config.models.genotype import GenotypeModel

from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase





router = APIRouter(
    prefix="/api",
    tags=["Genotypes"]
)


@router.get("/genotypes/{genotype_label}")
def get_genotype_by_label(genotype_label : str):
    """_summary_

    Parameters
    ----------
    genotype_label : str
        _description_
    """
    

@router.get("/genotypes", response_model=List[GenotypeModel])
def get_genotypes(proteome_id : Optional[str] = None, feature_key : Optional[str] = None):
    """Returns the genotypes defined using the params: ``proteome_id`` or ``feature_key``. 
    If feature_key is provided, the proteome_id is ingored. If ``proteome_id`` is given, then
    all genotypes that are defined for a given proteome_id is provided. 

    Parameters
    ----------
    proteome_id : Optional[str], optional
        _description_, by default None
    feature_key : _type_, optional
        _description_, by default Optional[str]=None
    """
    db_genotype = MCGenotypes.getGenotypeDatabase()
    try:
        genotypes = db_genotype.get(proteome_id=proteome_id,feature_key=feature_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return genotypes


@router.post("/genotypes")
def add_genotype(genotype : GenotypeModel):
    """_summary_

    Parameters
    ----------
    genotype : GenotypeModel
        _description_
    """
    db_genotype = MCGenotypes.getGenotypeDatabase()
    db_genotype.add(genotype=genotype)