from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.conditions_applications import ConditionApplicationAttributeModel
from config.models.samples import SampleResponseModel
from services.users import get_user_from_token
from typing import List, Dict

DB = Database.DB()

router = APIRouter(
    prefix="/api/samples",
    tags=["Samples", "Condition Applications"],
    )


@router.get("/{sample_tag}")
def get_sample(sample_tag : str, user : UserModel = Depends(get_user_from_token)) -> SampleResponseModel:
    "Returns the sample information for a given sample tag."
    if not DB.samples.exists(tag = sample_tag):
        raise HTTPException(status_code=404, detail=f"No sample found for tag {sample_tag}")
    
    sample = DB.samples.get(tag=sample_tag)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"Sample found for tag {sample_tag} but the DB returned None")
    S
    return sample 

@router.get("/{sample_tag}/ca")
def get_sample_condition_applications(sample_tag: str, group_by_attribute : bool = True, user: UserModel = Depends(get_user_from_token)) -> List[str]|List[ConditionApplicationAttributeModel]:
    "Return the condition applications for a given sample."
    return DB.samples.get_condition_procedure(tag = sample_tag, group_by_attribute=group_by_attribute)