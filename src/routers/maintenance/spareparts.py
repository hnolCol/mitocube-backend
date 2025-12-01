from typing import List 

from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from config.models.spareparts import SparepartResponseModel, SparepartInsertModel, SparepartBaseModel
from services.users import is_user_admin, get_user_from_token


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/spareparts",
    tags=["Maintenance", "Performance", "Spare parts"]
    )



@router.get("/q")
def find_spare_parts(search_string : str = "", limit : int = 20) -> List[str]:
    "Finds spare parts by a search_string and returns the tags. " 
    
    tag = DB.spareparts.find(search_string = search_string, limit = limit)
    return tag
    
@router.get("/{tag}", response_model=SparepartResponseModel)
def get_sparepart_by_tag(tag : str): 
    """Get a spare part by its tag."""
    
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404,detail="Spare part not found.")
        
    return DB.spareparts.get(tag = tag)


@router.get("/{tag}/text")
def get_text(tag : str) -> str:
    """Get spare part text by its tag."""

    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")
    print(DB.spareparts.get_text(tag = tag))
    return DB.spareparts.get_text(tag = tag)

@router.get("/{tag}/description")
def get_description(tag : str) -> str:       
    """Get spare part description by its tag.
    """
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")

    return DB.spareparts.get_description(tag = tag) 

@router.get("/{tag}/company")
def get_company(tag : str) -> str:       
    """Get spare part company by its tag.
    """
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")

    return DB.spareparts.get_company(tag = tag)

@router.get("/{tag}/product_id")
def get_product_id(tag : str) -> str:       
    """Get spare part product ID by its tag.
    """
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")

    return DB.spareparts.get_product_id(tag = tag)

@router.get("/{tag}/price")
def get_price(tag : str) -> float|int:
    """Get spare part price by its tag.
    """
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")

    return DB.spareparts.get_price(tag = tag)

@router.get("/{tag}/link")
def get_link(tag : str) -> str:
    """Get spare part link by its tag.
    """
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")

    print(DB.spareparts.get_link(tag = tag))
    return DB.spareparts.get_link(tag = tag)


@router.post("/")
def insert_sparepart(sparepart : SparepartInsertModel, user : UserModel = Depends(is_user_admin)) -> bool:
    """Adds a new spare part in the database."""
    
    ok = DB.spareparts.insert(sparepart=sparepart, user_tag = user.tag)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not add spare part to the database.")
    return ok


@router.put("/{tag}", response_model=bool)
def update_sparepart(sparepart : SparepartBaseModel, user : UserModel = Depends(is_user_admin)) -> bool:
    """Updates a spare part in the database."""
    
    ok = DB.spareparts.update(sparepart=sparepart, user_tag = user.tag)
 
    if not ok:
        raise HTTPException(status_code=500, detail="Could not update spare part in the database.")
    return ok

@router.delete("/{tag}")
def delete_sparepart(tag : str, user : UserModel = Depends(is_user_admin)) -> bool:
    """Deletes a spare part from the database."""
    
    if not DB.spareparts.exists(tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")
    
    ok = DB.spareparts.delete(tag = tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete spare part from the database.")
    
    return ok

