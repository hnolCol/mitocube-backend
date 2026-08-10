from fastapi import APIRouter, Depends, HTTPException
from typing import List
from config.models.external_resource import ExternalResourceInsertModel, ExternalResourceModel
from config.models.crosslink import CrosslinkModel, CrosslinkInsertModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin
from lib.database.Database import Database

DB = Database.DB()

router = APIRouter(
    prefix="/api/external-resources",
    tags=["ExternalResources"])


@router.post("")
def insert_external_resource(data: ExternalResourceInsertModel, user: UserModel = Depends(get_user_from_token)) -> ExternalResourceModel:
    """Inserts a new external resource (e.g. a publication). Admin only."""
    if not is_user_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required.")
    DB.external_resources.insert(data)
    return DB.external_resources.get(data.tag)


@router.post("/{tag}/crosslinks")
def insert_external_crosslinks(tag: str, data: List[CrosslinkInsertModel], user: UserModel = Depends(get_user_from_token)) -> dict:
    """Inserts a batch of XLs sourced from the given external resource. Admin only."""
    if not is_user_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required.")
    if not DB.external_resources.exists(tag):
        raise HTTPException(status_code=404, detail="External resource not found.")

    inserted, skipped = 0, 0
    for item in data:
        if DB.crosslinks.insert_external(item, resource_tag=tag):
            inserted += 1
        else:
            skipped += 1

    return {"inserted": inserted, "skipped": skipped}


@router.get("")
def find_external_resources(limit: int = None, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """Returns tags of all external resources."""
    return DB.external_resources.find(limit=limit)


@router.get("/{tag}")
def get_external_resource(tag: str, user: UserModel = Depends(get_user_from_token)) -> ExternalResourceModel:
    """Returns an external resource by its unique tag."""
    if not DB.external_resources.exists(tag):
        raise HTTPException(status_code=404, detail="External resource not found.")
    return DB.external_resources.get(tag)


@router.get("/{tag}/condition_applications")
def get_external_resource_condition_applications(tag: str, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """Returns condition-application tags (cell line, crosslinker, etc.) attached to a resource."""
    if not DB.external_resources.exists(tag):
        raise HTTPException(status_code=404, detail="External resource not found.")
    return DB.external_resources.get_condition_applications(tag=tag)


@router.get("/{tag}/crosslinks")
def find_crosslinks_by_resource(tag: str, limit: int = 100, user: UserModel = Depends(get_user_from_token)) -> List[CrosslinkModel]:
    """Returns crosslinks linked to the given external resource."""
    if not DB.external_resources.exists(tag):
        raise HTTPException(status_code=404, detail="External resource not found.")
    return DB.external_resources.find_crosslinks(resource_tag=tag, limit=limit)


@router.get("/protein/{protein_tag}")
def find_resources_by_protein(protein_tag: str, user: UserModel = Depends(get_user_from_token)) -> List[dict]:
    """Returns external resources that have crosslink annotations involving the given protein,
    with the crosslink count per resource."""
    return DB.external_resources.find_by_protein(protein_tag=protein_tag)