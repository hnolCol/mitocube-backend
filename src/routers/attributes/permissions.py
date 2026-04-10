from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from typing import List, Dict

DB = Database.DB()

router = APIRouter(
    prefix="/api/attributes",
    tags=["Permissions"],
)

# permission for attributes/traits for user, only curator can edit and delete, but everyone can create 
@router.get("/traits/permissions")
def get_permissions( user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:

    return PermissionResponseModel(user_tag = user.tag, 
                                   role = user.role, 
                                   insert = user.role >= UserRolesEnum.STANDARD, 
                                   delete = user.role >= UserRolesEnum.CURATOR,
                                   edit = user.role >= UserRolesEnum.CURATOR)   

