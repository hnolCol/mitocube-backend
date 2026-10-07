from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List
from config.models.diseases import DiseaseModel, DiseaseInputModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin

router = APIRouter(dependencies=[Depends(get_user_from_token)],prefix="/api/diseases", tags=["Diseases"])
not_found = HTTPException(status_code=404, detail="Disease not found.")

@router.get("")
def get_diseases(query: str = None, limit: int = 20, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[DiseaseModel]:
    if query:
        return db.diseases.find(query=query, limit=limit)
    return db.diseases.get(limit=limit)

@router.get("/{tag}")
def get_disease(tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> DiseaseModel:
    if not db.diseases.exists(tag): raise not_found
    return db.diseases.get(tags=[tag])[0]

@router.post("")
def insert_disease(disease: DiseaseInputModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    return db.diseases.insert(disease, user_tag=user.tag)

@router.delete("/{tag}")
def delete_disease(tag: str, user: UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    if not db.diseases.exists(tag): raise not_found
    return db.diseases.delete(tag)