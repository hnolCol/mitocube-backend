from typing import List, Dict
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException


from config.models.user import UserModel
from config.models.maintenance import MaintenanceProcedureResponseModel, MiantenanceProcedureInsertModel
from services.users import is_user_admin, get_user_from_token


# Miantenance procedure router
# This router handles the maintenance procedures, which are a set of instructions
# for performing maintenance tasks on instruments. Procedures can be searched by
# tags or by a search string, and can be created by users with admin privileges.
# The procedures are stored in the database and can be retrieved by their tags. 
# An example for a maintenance procedure would be "Cleaning the instrument's quadrupole".


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/maintenance/procedures",
    tags=["Maintenance", "Performance", "Procedure"]
    )



@router.get("/q")       
def get_procedure_by_search_string(search_string : str = None, limit : int = 20, db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Get a maintenance procedure by search string"
    
    procedure_tags = db.maintenance_procedures.find(search_string = search_string, 
                                       limit = limit)
    return procedure_tags


@router.get("/{procedure_tag}")
def get_procedure(procedure_tag : str, db : DatabaseABC = Depends(get_db)) -> MaintenanceProcedureResponseModel:
    """Returns a maintenance procedure by a tag."""
    if not db.maintenance_procedures.exists(tag = procedure_tag): 
        raise HTTPException(status_code=404, detail="Procedure not found.")
    
    return db.maintenance_procedures.get(tag = procedure_tag)


@router.get("/{procedure_tag}/text")
def get_text(procedure_tag : str, db : DatabaseABC = Depends(get_db)) -> str:
    """Get procudure text by its tag.

    Parameters
    ----------
    tag : str
        The procedure tag.

    Returns
    -------
    str
        The procedure text.
    """
    if not db.maintenance_procedures.exists(tag = procedure_tag):
        raise HTTPException(status_code=404, detail="Procedure not found.")
    return db.maintenance_procedures.get_text(tag = procedure_tag)


@router.get("/{procedure_tag}/description")
def get_description(procedure_tag : str, db : DatabaseABC = Depends(get_db)) -> str:           
    """Get procedure description by its tag.

    Parameters
    ----------
    tag : str
        The procedure tag.

    Returns
    -------
    str
        The procedure description.
    """
    if not db.maintenance_procedures.exists(tag = procedure_tag):
        raise HTTPException(status_code=404, detail="procedure not found.")
    
    return db.maintenance_procedures.get_description(tag = procedure_tag)

@router.get("/{procedure_tag}/priority")
def get_priority(procedure_tag : str, db : DatabaseABC = Depends(get_db)) -> int:           
    """Get procedure priority by its tag.

    Parameters
    ----------
    tag : str
        The procedure tag.

    Returns
    -------
    int
        The procedure priority.
    """
    if not db.maintenance_procedures.exists(tag = procedure_tag):
        raise HTTPException(status_code=404, detail="procedure not found.")
    
    return db.maintenance_procedures.get_priority(tag = procedure_tag)


@router.post("/", response_model=bool)
def insert_procedure(procedure : MiantenanceProcedureInsertModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    
    """Creates a new maintenance procedure."""

    ok = db.maintenance_procedures.insert(procedure, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert procedure into the database.")
    #background_tasks.add_task(db.maintenance_procedures._utils_insert_from_file)

    return ok

@router.put("/{procedure_tag}", response_model=bool)
def update_procedure( procedure : MaintenanceProcedureResponseModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    """Update a procedure in the database. Requires admin rights.

    Parameters
    ----------
    
        The procedure to update.

    Returns
    -------
    bool
        True if the procedure was updated successfully, False otherwise.
    """
    
    ok = db.maintenance_procedures.update(procedure=procedure, user_tag=user.tag)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not update procedure in the database.")

    return ok

@router.delete("/{procedure_tag}")
def delete_procedure(procedure_tag : str, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    """Deletes a maintenance procedure by its tag."""
    
    if not db.maintenance_procedures.exists(procedure_tag):
        raise HTTPException(status_code=404, detail="Procedure not found.")

    ok = db.maintenance_procedures.delete(tag = procedure_tag)
    return ok
    







