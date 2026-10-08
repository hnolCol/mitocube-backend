

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from services.submission import check_submission_access
from typing import List, Dict


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions",
    tags=["Permissions"],
)

@router.get("/permissions")
def get_permissions(user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:
    """Fetches the permissions for the current user for submissions."""
    return PermissionResponseModel(user_tag=user.tag, create= user.role >= UserRolesEnum.STANDARD, archive= user.role >= UserRolesEnum.CURATOR, comment = user.role >= UserRolesEnum.STANDARD, download= user.role >= UserRolesEnum.STANDARD, edit = user.role >= UserRolesEnum.CURATOR,  upload = user.role >= UserRolesEnum.CURATOR, state_change= user.role >= UserRolesEnum.CURATOR, role=user.role) 

@router.get("/{submission_tag}/permissions")
def get_submission_permissions(submission_tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PermissionResponseModel:
    # Fetch and return the permissions for the specified submission
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    has_access = True
    user_tag = db.submissions.get_creator(tag = submission_tag) # Ensure the submission exists
    is_creator = (user.tag == user_tag)
    is_at_least_curator = (user.role >= UserRolesEnum.CURATOR)  # Assuming curator has access to all submissions
    return PermissionResponseModel(user_tag = user.tag, 
                                   view = has_access,
                                   role = user.role,
                                   tag = submission_tag,
                                   edit = is_creator or is_at_least_curator, 
                                   delete = is_creator or is_at_least_curator,
                                   upload = is_at_least_curator,
                                   state_change= is_at_least_curator,
                                   download= user.role >= UserRolesEnum.STANDARD and has_access,
                                   comment = user.role >= UserRolesEnum.STANDARD and has_access) 
    