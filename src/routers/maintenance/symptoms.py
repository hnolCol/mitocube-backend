from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.performance import QCRunModel
from config.models.user import UserModel
from config.models.symptoms import SymptomModel, SymptomResponseModel, SymptomInsertModel
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
    return DB.symptoms.get(tag = symptom_tag)


@router.post("/", response_model=bool)
def add_symptom(symptom : SymptomInsertModel, user : UserModel = Depends(is_user_admin)) -> bool:
    """Add a symptom to the database. Requires admin rights.

    Parameters
    ----------
    symptom : SymptomModel
        The symptom to add

    Returns
    -------
    bool
        True if the symptom was added successfully, False otherwise.
    """
    ok = DB.symptoms.insert(symptom)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert symptom in the database.")
    return ok


@router.put("/", response_model=bool)
def update_symptom(symptom : SymptomInsertModel, user : UserModel = Depends(is_user_admin)) -> bool:
    """Update a symptom in the database. Requires admin rights.

    Parameters
    ----------
    symptom : SymptomInsertModel
        The symptom to update.

    Returns
    -------
    bool
        True if the symptom was updated successfully, False otherwise.
    """
    ok = DB.symptoms.update(symptom)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not update symptom in the database.")
    return ok
    
@router.delete("/{symptom_tag}", response_model=bool)
def delete_symptom(symptom_tag : str, user : UserModel = Depends(is_user_admin)) -> bool:
    """Delete a symptom from the database. Requires admin rights.

    Parameters
    ----------
    symptom_tag : str
        The tag of the symptom to delete.

    Returns
    -------
    bool
        True if the symptom was deleted successfully, False otherwise.
    """
    if not DB.symptoms.exists(symptom_tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    ok = DB.symptoms.delete(tag = symptom_tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete symptom from the database.")
    return oks