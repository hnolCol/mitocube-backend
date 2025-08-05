from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from config.models.spareparts import SparepartResponseModel
from services.users import is_user_admin, get_user_from_token


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/spareparts",
    tags=["Maintenance", "Performance", "Spare parts"]
    )



@router.get("/q")
def find_spare_parts(search_string : str = "", limit : int = 20) -> List[str]:
    "Finds spare parts by a search_string and returns the tags. " 
    
    return DB.spareparts.find(search_string = search_string, limit = limit)
    
@router.get("/{tag}")
def get_sparepart_by_tag(tag : str) -> SparepartResponseModel:
    ""
    
    if not DB.spareparts.exists(tag = tag):
        raise HTTPException(status_code=404,detail="Spare part not found.")
    spare_part = DB.spareparts.get(tag = tag)
        
    return spare_part