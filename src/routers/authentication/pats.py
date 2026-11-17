from typing import List

from fastapi import APIRouter, Depends, HTTPException

from config.models.pat import PATCreatedResponseModel, PATCreationBlockModel, PATInsertModel, PATResponseModel
from config.models.user import UserModel
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from services.pats import get_pat_expires_at_epochmillis
from services.users import get_user_from_token, is_user_admin

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/auth/pats",
    tags=["Token", "Personal Access Tokens"]
)


@router.post("", response_description="Creates a personal access token. The plain token is only shown once.",
             response_model=PATCreatedResponseModel)
def create_pat(props : PATInsertModel, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PATCreatedResponseModel:
    """Creates a personal access token (PAT) for the logged in user.

    The token is shown exactly once in the response and should be stored in
    the environment of the script that uses it. Only the SHA-256 hash of the
    token is stored in the database.
    """
    try:
        pat, token = db.pats.create(user_tag=user.tag,
                                    name=props.name,
                                    scopes=[s.value for s in props.scopes],
                                    expires_at_epochmillis=get_pat_expires_at_epochmillis(props.expires_in_days))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return PATCreatedResponseModel(**pat.model_dump(), token=token)


@router.get("", response_description="Returns all personal access tokens of the logged in user.",
            response_model=List[PATResponseModel])
def list_pats(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[PATResponseModel]:
    """Returns the metadata of all personal access tokens of the logged in user."""
    return db.pats.list(user_tag=user.tag)


@router.delete("/{pat_tag}", response_description="Revokes one of the personal access tokens of the logged in user.")
def revoke_pat(pat_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> dict:
    """Revokes the personal access token with the given tag.

    The token must belong to the logged in user. Revoked tokens immediately
    stop working.
    """
    if not db.pats.revoke(user_tag=user.tag, pat_tag=pat_tag):
        raise HTTPException(status_code=404, detail=f"No personal access token with tag '{pat_tag}' found.")
    return {"success": True, "tag": pat_tag, "revoked": True}


@router.get("/user/{user_tag}", response_description="Returns all personal access tokens of a user. Requires admin rights.",
            response_model=List[PATResponseModel])
def list_user_pats(user_tag : str, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> List[PATResponseModel]:
    """Returns the metadata of all personal access tokens of the given user.

    Admin only: allows inspecting a user's tokens, e.g. to investigate misuse.
    """
    return db.pats.list(user_tag=user_tag)


@router.delete("/admin/{pat_tag}", response_description="Revokes any personal access token. Requires admin rights.")
def revoke_pat_as_admin(pat_tag : str, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> dict:
    """Revokes the personal access token with the given tag, regardless of the owner.

    Admin only: intended for incident response, e.g. a leaked or misused
    token. Records which admin revoked the token and when.
    """
    if not db.pats.revoke_by_admin(pat_tag=pat_tag, revoked_by=user.tag):
        raise HTTPException(status_code=404, detail=f"No active personal access token with tag '{pat_tag}' found.")
    return {"success": True, "tag": pat_tag, "revoked": True, "revoked_by": user.tag}


@router.patch("/user/{user_tag}/creation", response_description="Blocks or unblocks personal access token creation of a user. Requires admin rights.")
def set_pat_creation_blocked(user_tag : str, props : PATCreationBlockModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> dict:
    """Blocks or unblocks the creation of personal access tokens for the given user.

    Admin only: useful to wind down API access without fully blocking the
    account. Existing tokens keep working until they expire or are revoked.
    """
    if not db.pats.set_creation_blocked(user_tag=user_tag, blocked=props.blocked):
        raise HTTPException(status_code=404, detail=f"No user with tag '{user_tag}' found.")
    return {"success": True, "user_tag": user_tag, "creation_blocked": props.blocked}
