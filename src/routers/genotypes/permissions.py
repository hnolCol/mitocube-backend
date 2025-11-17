from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel 
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token
from typing import List, Dict

DB = Database.DB()

router = APIRouter(
    prefix="/api/genotypes",
    tags=["Permissions"],
)

# permission for genotype for user, only curator can edit and delete, but everyone can create 
@router.get("/{genotype_tag}/permissions")
def get_permissions(genotype_tag : str, user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:

    return PermissionResponseModel(user_tag = user.tag, 
                                   role = user.role, 
                                   insert = user.role >= UserRolesEnum.STANDARD, 
                                   delete = user.role >= UserRolesEnum.CURATOR,
                                   edit = user.role >= UserRolesEnum.CURATOR)

