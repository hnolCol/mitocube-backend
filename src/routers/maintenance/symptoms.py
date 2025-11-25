from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.performance import QCRunModel
from config.models.user import UserModel
from config.models.symptoms import SymptomResponseModel, SymptomInsertModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import is_user_admin, get_user_from_token


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/symptoms",
    tags=["Maintenance", "Performance", "Symptoms"]
    )

@router.get("/q")
def get_symptom_by_search_string(search_string : str = "", limit : int = 20) -> List[str]:
    "Get a symptom by tag or by search string"
    
    tag = DB.symptoms.find(search_string = search_string, 
                                    limit = limit)
    return tag

@router.get("/{tag}", response_model=SymptomResponseModel)
def get_symptom(tag: str):
    if not DB.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    return DB.symptoms.get(tag=tag)

@router.get("/{tag}/text")
def get_text(tag : str) -> str:
    """Get symptom text by its tag.

    Parameters
    ----------
    tag : str
        The symptom tag.

    Returns
    -------
    str
        The symptom text.
    """
    if not DB.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    return DB.symptoms.get_text(tag = tag)  

@router.get("/{tag}/description")
def get_description(tag : str) -> str:           
    """Get symptom description by its tag.

    Parameters
    ----------
    tag : str
        The symptom tag.

    Returns
    -------
    str
        The symptom description.
    """
    if not DB.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    return DB.symptoms.get_description(tag = tag)

@router.get("/{tag}/priority")
def get_priority(tag : str) -> int:           
    """Get symptom priority by its tag.

    Parameters
    ----------
    tag : str
        The symptom tag.

    Returns
    -------
    int
        The symptom priority.
    """
    if not DB.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    return DB.symptoms.get_priority(tag = tag)


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
    ok = DB.symptoms.insert(symptom=symptom, user_tag=user.tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert symptom in the database.")
    return ok


@router.put("/{tag}", response_model=bool)
def update_symptom(tag: str, symptom : SymptomInsertModel, user : UserModel = Depends(is_user_admin)) -> bool:
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

    ok = DB.symptoms.update(tag = tag, symptom=symptom, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not update symptom in the database.")

    return ok
    
@router.delete("/{tag}", response_model=bool)
def delete_symptom(tag : str, user : UserModel = Depends(is_user_admin)) -> bool:
    """Delete a symptom from the database. Requires admin rights.

    Parameters
    ----------
    tag : str
        The tag of the symptom to delete.

    Returns
    -------
    bool
        True if the symptom was deleted successfully, False otherwise.
    """
    if not DB.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    ok = DB.symptoms.delete(tag = tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete symptom from the database.")
    return ok

