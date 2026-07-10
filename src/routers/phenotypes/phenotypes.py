from fastapi import APIRouter, Depends, HTTPException
from typing import List
from services.users import get_user_from_token, is_user_admin
from services.random_generators import get_random_string
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.phenotype import PhenotypeModel, PhenotypeInputModel

DB = Database.DB()
router = APIRouter(prefix="/api/phenotypes", tags=["Phenotypes"])
not_found = HTTPException(status_code=404, detail="Phenotype not found.")

@router.get("")
def get_phenotypes(query: str = None, limit: int = 20, user: UserModel = Depends(get_user_from_token)) -> List[PhenotypeModel]:
    if query is not None:
        return DB.phenotypes.find(query=query, limit=limit)
    return DB.phenotypes.get(limit=limit)

@router.get("/{tag}")
def get_phenotype_by_tag(tag: str, user: UserModel = Depends(get_user_from_token)) -> PhenotypeModel:
    results = DB.phenotypes.get(tags=[tag])
    if not results:
        raise not_found
    return results[0]

@router.post("")
def insert_phenotype(phenotype: PhenotypeInputModel, user: UserModel = Depends(get_user_from_token)) -> str:
    """Insert a manually-created phenotype (e.g. not yet in HPO) and return its tag."""
    tag = phenotype.tag or get_random_string(8)
    to_insert = PhenotypeInputModel(
        tag=tag,
        text=phenotype.text,
        description=phenotype.description,
        group_tag=phenotype.group_tag or tag,
        group_text=phenotype.group_text or phenotype.text,
    )
    DB.phenotypes.insert(to_insert)
    return tag