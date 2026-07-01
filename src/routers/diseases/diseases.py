from fastapi import APIRouter, Depends, HTTPException
from typing import List
from config.models.diseases import DiseaseModel, DiseaseInputModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin
from lib.database.Database import Database

DB = Database.DB()
router = APIRouter(prefix="/api/diseases", tags=["Diseases"])
not_found = HTTPException(status_code=404, detail="Disease not found.")

@router.get("")
def get_diseases(query: str = None, limit: int = 20, user: UserModel = Depends(get_user_from_token)) -> List[DiseaseModel]:
    if query:
        return DB.diseases.find(query=query, limit=limit)
    return DB.diseases.get(limit=limit)

@router.get("/{tag}")
def get_disease(tag: str, user: UserModel = Depends(get_user_from_token)) -> DiseaseModel:
    if not DB.diseases.exists(tag): raise not_found
    return DB.diseases.get(tags=[tag])[0]

@router.post("")
def insert_disease(disease: DiseaseInputModel, user: UserModel = Depends(get_user_from_token)) -> bool:
    return DB.diseases.insert(disease, user_tag=user.tag)

@router.delete("/{tag}")
def delete_disease(tag: str, user: UserModel = Depends(is_user_admin)) -> bool:
    if not DB.diseases.exists(tag): raise not_found
    return DB.diseases.delete(tag)