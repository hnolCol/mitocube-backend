from fastapi import APIRouter, HTTPException, Depends
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_at_least_curator
from config.models.submissions.metatexts import MetaTextResponseModel, MetaTextInsertModel
from lib.database.Database import Database


DB = Database.DB()

router = APIRouter(
    prefix="/api/metatexts",
    tags=["Metatexts"],
    )



@router.get("/{tag}")
def get_metatext(tag : str, user : UserModel = Depends(get_user_from_token)) -> MetaTextResponseModel:
    "Returns the metatext with the given tag."

    if not DB.metatexts.exists(tag=tag):
        raise HTTPException(status_code=404, detail=f"Metatext associated with the {tag} not found")
    metatext = DB.metatexts.get(tag=tag)
    MetaTextResponseModel(**metatext)
    return metatext


@router.patch("/{tag}")
def update_metatext(tag: str, metatext: MetaTextInsertModel, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Updates the metatext with the given tag."

    if not DB.metatexts.exists(tag=tag):
        raise HTTPException(status_code=404, detail=f"Metatext associated with the {tag} not found")
    ok = DB.metatexts.update(tag=tag, title=metatext.title, text=metatext.text, user_tag = user.tag)
    return ok


@router.delete("/{tag}")
def delete_metatext(tag: str, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    "Deletes the metatext with the given tag."

    if not DB.metatexts.exists(tag=tag):
        raise HTTPException(status_code=404, detail=f"Metatext associated with the {tag} not found")
    ok = DB.metatexts.delete(tag=tag)
    return ok

