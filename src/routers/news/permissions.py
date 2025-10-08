from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal

# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.database.Database import Database
from config.models.permissions import PermissionResponseModel 
from config.models.user import UserModel

from config.enums.users.roles import UserRolesEnum
from services.users import is_user_admin, get_user_from_token

DB = Database.DB()


router = APIRouter(
    prefix="/api/news",
    tags=["News"]
    )



@router.get("/permissions")
def get_news_permissions(user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:
    
    return PermissionResponseModel(
        user_tag= user.tag,
        create= user.role > UserRolesEnum.CURATOR,
        edit= user.role > UserRolesEnum.CURATOR,
        delete= user.role > UserRolesEnum.CURATOR,
    )
