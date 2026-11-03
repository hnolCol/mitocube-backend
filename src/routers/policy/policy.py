from typing import List

from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from config.models.user import UserModel
from config.models.Policy import PolicyModel, PolicyInsertModel, PolicyUpdateModel, PolicyStatusModel
from services.users import get_user_from_token, is_user_admin


router = APIRouter(
    prefix="/api/policy",
    tags=["Policy"]
)


@router.get("")
def get_policies(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[PolicyModel]:
    "Returns all policies."
    return db.policy.list()


@router.get("/status")   # has to stay above "/{tag}", otherwise "status" is read as a tag
def get_policy_status(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[PolicyStatusModel]:
    "Returns for every policy whether the current user has to agree to it."
    return db.policy.get_status(user_tag=user.tag)


@router.post("", summary="Create a policy. Requires admin rights.")
def create_policy(policy : PolicyInsertModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> PolicyModel:
    try:
        return db.policy.create(policy=policy, user_tag=user.tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{tag}")
def get_policy(tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PolicyModel:
    policy = db.policy.get(tag)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return policy


@router.put("/{tag}", summary="Update a policy. Requires admin rights.")
def update_policy(tag : str, policy : PolicyUpdateModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> PolicyModel:
    updated = db.policy.update(tag=tag, policy=policy, user_tag=user.tag)
    if updated is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return updated


@router.delete("/{tag}", summary="Delete a policy. Requires admin rights.")
def delete_policy(tag : str, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    if not db.policy.delete(tag):
        raise HTTPException(status_code=404, detail="Policy not found.")
    return True


@router.post("/{tag}/agree")
def agree_to_policy(tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    "The current user agrees to the current version of the policy."
    if db.policy.get(tag) is None:
        raise HTTPException(status_code=404, detail="Policy not found.")
    return db.policy.agree(tag=tag, user_tag=user.tag)