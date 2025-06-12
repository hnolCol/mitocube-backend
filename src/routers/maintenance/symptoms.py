from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.performance import QCRunModel
from config.models.user import UserModel
from config.models.symptoms import SymptomModel, SymptomResponseModel
from services.users import is_user_admin, get_user_from_token


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/symptoms",
    tags=["Maintenance", "Performance", "Symptoms"]
    )

@router.get("/q")
def get_symptom_by_search_string(search_string : str = "", limit : int = 20) -> List[str]:
    "Get a symptom by tag or by search string"
    
    symptom_tags = DB.symptoms.find(search_string = search_string, 
                                    limit = limit)
        
    return symptom_tags

@router.get("/{symptom_tag}")
def get(symptom_tag : str) -> SymptomResponseModel:
    ""
    if not DB.symptoms.exists(tag = symptom_tag): raise HTTPException(status_code=404, detail="Symptom not found.")
    print(DB.symptoms.get(tag = symptom_tag))
    return DB.symptoms.get(tag = symptom_tag)






    
    
    
    