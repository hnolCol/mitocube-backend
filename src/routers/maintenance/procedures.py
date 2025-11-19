from typing import List, Dict

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from config.models.maintenance import MaintenanceProcedureResponseModel
from services.users import is_user_admin, get_user_from_token


# Miantenance procedure router
# This router handles the maintenance procedures, which are a set of instructions
# for performing maintenance tasks on instruments. Procedures can be searched by
# tags or by a search string, and can be created by users with admin privileges.
# The procedures are stored in the database and can be retrieved by their tags. 
# An example for a maintenance procedure would be "Cleaning the instrument's quadrupole".

DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/procedures",
    tags=["Maintenance", "Performance", "Procedure"]
    )



@router.get("/q")       
def get_procedure_by_search_string(search_string : str = "", limit : int = 20) -> List[str]:
    "Get a maintenance procedure by search string"
    
    procedure_tags = DB.maintenance_procedures.find(search_string = search_string, 
                                       limit = limit)
        
    return procedure_tags


@router.get("/{procedure_tag}")
def get(procedure_tag : str) -> MaintenanceProcedureResponseModel:
    """Returns a maintenance procedure by a tag."""
    if not DB.maintenance_procedures.exists(tag = procedure_tag): 
        raise HTTPException(status_code=404, detail="Procedure not found.")
    
    return DB.maintenance_procedures.get(tag = procedure_tag)

@router.post("/")
def create_procedure(procedure : Dict, user : UserModel = Depends(is_user_admin)) -> bool:
    
    """Creates a new maintenance procedure."""

    
    if DB.maintenance_procedures.exists(tag = procedure["tag"]):
        raise HTTPException(status_code=400, detail="Procedure with this tag already exists.")
    
    ok = DB.maintenance_procedures.create(procedure)
    #background_tasks.add_task(DB.maintenance_procedures._utils_insert_from_file)

    return ok

@router.delete("/{procedure_tag}")
def delete_procedure(procedure_tag : str, user : UserModel = Depends(is_user_admin)) -> bool:
    """Deletes a maintenance procedure by its tag."""
    
    if not DB.maintenance_procedures.exists(tag = procedure_tag):
        raise HTTPException(status_code=404, detail="Procedure not found.")

    ok = DB.maintenance_procedures.delete(tag = procedure_tag)
    return ok
    







