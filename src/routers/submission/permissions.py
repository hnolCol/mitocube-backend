

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from typing import List, Dict

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Permissions"],
)

@router.get("/permissions")
def get_permissions(user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:
    """Fetches the permissions for the current user for submissions."""
    return PermissionResponseModel(user_tag=user.tag, create= user.role >= UserRolesEnum.STANDARD, archive= user.role >= UserRolesEnum.CURATOR, comment = user.role >= UserRolesEnum.STANDARD, download= user.role >= UserRolesEnum.STANDARD) 

@router.get("/{submission_tag}/permissions")
def get_submission_permissions(submission_tag: str, user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:
    # Fetch and return the permissions for the specified submission
    if not DB.submissions.exists(tag = submission_tag):
        raise HTTPException(status_code=404, detail=f"Submission with tag {submission_tag} not found")
    user_tag = DB.submissions.get_creator(tag = submission_tag)  # Ensure the submission exists
    is_creator = (user.tag == user_tag)
    is_at_least_curator = (user.role >= UserRolesEnum.CURATOR)  # Assuming curator 

    return PermissionResponseModel(user_tag = user.tag, 
                                   role = user.role,
                                   tag = submission_tag,
                                   edit = is_creator or is_at_least_curator, 
                                   delete = is_creator or is_at_least_curator,
                                   upload = is_at_least_curator,
                                   state_change= is_at_least_curator,
                                   download= user.role >= UserRolesEnum.STANDARD,
                                   comment = user.role >= UserRolesEnum.STANDARD) 
    