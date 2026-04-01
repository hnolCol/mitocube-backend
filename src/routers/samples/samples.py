from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationAttributeModel
from config.models.samples import SampleResponseModel, SampleUpdateModel
from services.users import get_user_from_token
from typing import List, Dict, Optional

DB = Database.DB()

router = APIRouter(
    prefix="/api/samples",
    tags=["Samples", "Condition Applications"],
    )


@router.get("/count", summary="Get the total number of samples in the database.")
def get_sample_count(protein_group_tag : str = None, submission_tag : str = None, genotype_tag : str = None, trait_tag : str = None, has_protein_quantification : bool = False, has_peptide_quantification : bool = False, user : UserModel = Depends(get_user_from_token)) -> int:
    "Returns the total number of samples in the database."
    return DB.samples.count(protein_group_tag=protein_group_tag, submission_tag=submission_tag, trait_tag=trait_tag, has_protein_quantification=has_protein_quantification, has_peptide_quantification=has_peptide_quantification)



@router.get("/{sample_tag}")
def get_sample(sample_tag : str, user : UserModel = Depends(get_user_from_token)):
    "Returns the sample information for a given sample tag."
    if not DB.samples.exists(tag = sample_tag):
        raise HTTPException(status_code=404, detail=f"No sample found for tag {sample_tag}")
    
    sample = DB.samples.get(tag=sample_tag)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"Sample found for tag {sample_tag} but the DB returned None")
    return sample 

@router.get("/{sample_tag}/ca")
def get_sample_condition_applications(sample_tag: str, group_by_attribute : bool = True, user: UserModel = Depends(get_user_from_token)) -> List[str]|List[ConditionApplicationAttributeModel]:
    "Return the condition applications for a given sample."
    return DB.samples.get_condition_applications(tag = sample_tag, group_by_attribute=group_by_attribute)


@router.get("/{sample_tag}/genotype")
def get_sample_genotype(sample_tag : str, user: UserModel = Depends(get_user_from_token)) -> Optional[str]:
    "Return the genotype for the given sample."
    return DB.samples.get_sample_genotype(tag = sample_tag)


# @router.put("/{sample_tag}")
# def update_sample(sample_tag: str, data: SampleUpdateModel, user: UserModel = Depends(get_user_from_token)) -> bool:
#     if not DB.samples.exists(tag=sample_tag):
#         raise HTTPException(status_code=404, detail=f"No sample found for tag {sample_tag}")
#     DB.samples.update(
#         tag=sample_tag,
#         genotype_tag=data.genotype_tag,
#         condition_applications=data.condition_applications
#     )
#     if data.replicate is not None:
#         DB.samples.set_replicate(tag=sample_tag, replicate=data.replicate)
#     return True


@router.put("/{sample_tag}")
def update_sample(sample_tag: str, data: SampleUpdateModel, user: UserModel = Depends(get_user_from_token)) -> bool:
    if not DB.samples.exists(tag=sample_tag):
        raise HTTPException(status_code=404, detail=f"No sample found for tag {sample_tag}")
    DB.samples.update(tag=sample_tag, data=data)
    return True