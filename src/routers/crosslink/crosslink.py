from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List
from config.models.crosslink import CrosslinkInsertModel, CrosslinkModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/crosslinks", 
    tags=["Crosslinks"])


@router.post("")
def insert_crosslink(data: CrosslinkInsertModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """Inserts a new crosslink into the database. Returns True if successful, False otherwise."""
    
    ok = db.crosslinks.insert(data, user_tag=user.tag)
    return ok   

@router.get("/{tag}")
def get_crosslink(tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> CrosslinkModel:
    """Returns a crosslink by its unique tag."""
    if not db.crosslinks.exists(tag):
        raise HTTPException(status_code=404, detail="Crosslink not found.")
    return db.crosslinks.get(tag)   

@router.get("/protein/{protein_tag}")
def find_crosslinks_by_protein(protein_tag: str, resource_tag: str = None, limit: int = None, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[CrosslinkModel]:
    """Searches for crosslinks associated with the given protein tag, optionally filtered
    by external resource. Returns a list of matching crosslinks up to the specified limit."""
    return db.crosslinks.find(protein_tag=protein_tag, resource_tag=resource_tag, limit=limit)