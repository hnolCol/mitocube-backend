from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from typing import List, Dict

DB = Database.DB()

router = APIRouter(
    prefix="/api/annotations",
    tags=["Permissions"],
)


@router.get("/{tag}/permissions")
def get_annotation_permissions(user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:

    return PermissionResponseModel(user_tag = user.tag, 
                                   role = user.role, 
                                   insert = user.role >= UserRolesEnum.STANDARD, 
                                   delete = user.role >= UserRolesEnum.CURATOR,
                                   edit = user.role >= UserRolesEnum.CURATOR)   
