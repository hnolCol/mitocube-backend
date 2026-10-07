from fastapi import APIRouter, HTTPException, Depends
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_at_least_curator
from lib.database.Database import get_db
from config.models.submissions.metatexts import MetaTextResponseModel, MetaTextInsertModel
from lib.database.abstract.Database import DatabaseABC



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/metatexts",
    tags=["Metatexts"],
    )



@router.get("/{tag}")
def get_metatext(tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> MetaTextResponseModel:
    "Returns the metatext with the given tag."

    if not db.metatexts.exists(tag=tag):
        raise HTTPException(status_code=404, detail=f"Metatext associated with the {tag} not found")
    metatext = db.metatexts.get(tag=tag)
    MetaTextResponseModel(**metatext)
    return metatext


@router.patch("/{tag}")
def update_metatext(tag: str, metatext: MetaTextInsertModel, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    "Updates the metatext with the given tag."

    if not db.metatexts.exists(tag=tag):
        raise HTTPException(status_code=404, detail=f"Metatext associated with the {tag} not found")
    ok = db.metatexts.update(tag=tag, title=metatext.title, text=metatext.text, user_tag = user.tag)
    return ok


@router.delete("/{tag}")
def delete_metatext(tag: str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Deletes the metatext with the given tag."

    if not db.metatexts.exists(tag=tag):
        raise HTTPException(status_code=404, detail=f"Metatext associated with the {tag} not found")
    ok = db.metatexts.delete(tag=tag)
    return ok

