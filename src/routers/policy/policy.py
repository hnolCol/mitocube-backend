from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from config.models.user import UserModel
from config.models.Policy import PolicyModel, PolicyUpdateModel, PolicyStatusModel
from services.users import get_user_from_token, is_user_admin


router = APIRouter(
    prefix="/api/policy",
    tags=["Policy"]
)


@router.get("")
def get_policy(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PolicyModel:
    "Returns the current policy."
    policy = db.policy.get()
    if policy is None:
        raise HTTPException(status_code=404, detail="No policy defined.")
    return policy


@router.get("/status")
def get_policy_status(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PolicyStatusModel:
    "Returns whether the current user has to agree to the policy."
    return db.policy.get_status(user_tag=user.tag)


@router.post("/agree")
def agree_to_policy(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    "The current user agrees to the current policy."
    if db.policy.get() is None:
        raise HTTPException(status_code=404, detail="No policy defined.")
    return db.policy.agree(user_tag=user.tag)


@router.put("", summary="Create or update the policy. Requires admin rights.")
def update_policy(policy : PolicyUpdateModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> PolicyModel:
    return db.policy.update(policy=policy, user_tag=user.tag)