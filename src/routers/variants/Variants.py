from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List
from config.models.variants import VariantModel, VariantInputModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin

router = APIRouter(dependencies=[Depends(get_user_from_token)],prefix="/api/variants", tags=["Variants"])
not_found = HTTPException(status_code=404, detail="Variant not found.")

@router.get("/{tag}")
def get_variant(tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> VariantModel:
    if not db.variants.exists(tag): raise not_found
    return db.variants.get(tag)

@router.get("")
def find_variants(protein_tag: str = None, disease_tag: str = None, limit: int = 20, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[VariantModel]:
    if protein_tag:
        return db.variants.find_by_protein(protein_tag=protein_tag, limit=limit)
    if disease_tag:
        return db.variants.find_by_disease(disease_tag=disease_tag, limit=limit)
    raise HTTPException(status_code=400, detail="Provide either protein_tag or disease_tag.")

@router.delete("/{tag}")
def delete_variant(tag: str, user: UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    if not db.variants.exists(tag): raise not_found
    return db.variants.delete(tag)