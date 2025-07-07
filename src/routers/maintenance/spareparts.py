from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from services.users import is_user_admin, get_user_from_token


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/spareparts",
    tags=["Maintenance", "Performance", "Spare parts"]
    )



@router.get("/q")
def find_spare_parts(search_string : str = "") -> List[str]:
    "Finds spare parts by a search_string and returns the tags. " 
    
    return DB.spareparts.find(search_string = search_string)
    
@router.get("/{tag}")
def get_sparepart_by_tag(tag : str):
    ""
    DB.spareparts.get(tag = tag)