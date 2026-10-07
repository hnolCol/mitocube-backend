from typing import List 
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException


from config.models.user import UserModel
from config.models.symptoms import SymptomResponseModel, SymptomInsertModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import is_user_admin, get_user_from_token



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/maintenance/symptoms",
    tags=["Maintenance", "Performance", "Symptoms"]
    )

@router.get("/q")
def get_symptom_by_search_string(search_string : str = "", limit : int = 20, db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Get a symptom by tag or by search string"
    
    tag = db.symptoms.find(search_string = search_string, 
                                    limit = limit)
    return tag

@router.get("/{tag}", response_model=SymptomResponseModel)
def get_symptom(tag: str, db : DatabaseABC = Depends(get_db)):
    if not db.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    return db.symptoms.get(tag=tag)

@router.get("/{tag}/text")
def get_text(tag : str, db : DatabaseABC = Depends(get_db)) -> str:
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
    if not db.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    return db.symptoms.get_text(tag = tag)  

@router.get("/{tag}/description")
def get_description(tag : str, db : DatabaseABC = Depends(get_db)) -> str:           
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
    if not db.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    return db.symptoms.get_description(tag = tag)

@router.get("/{tag}/priority")
def get_priority(tag : str, db : DatabaseABC = Depends(get_db)) -> int:           
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
    if not db.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    return db.symptoms.get_priority(tag = tag)


@router.post("/", response_model=bool)
def add_symptom(symptom : SymptomInsertModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
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
    ok = db.symptoms.insert(symptom=symptom, user_tag=user.tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert symptom in the database.")
    return ok


@router.put("/{tag}", response_model=bool)
def update_symptom(tag: str, symptom : SymptomInsertModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
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

    ok = db.symptoms.update(tag = tag, symptom=symptom, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not update symptom in the database.")

    return ok
    
@router.delete("/{tag}", response_model=bool)
def delete_symptom(tag : str, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
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
    if not db.symptoms.exists(tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    ok = db.symptoms.delete(tag = tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete symptom from the database.")
    return ok

