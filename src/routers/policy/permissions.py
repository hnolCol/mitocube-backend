from fastapi import APIRouter, Depends
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel
from config.enums.users.roles import UserRolesEnum
from services.users import get_user_from_token


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/policy",
    tags=["Permissions"],
)


@router.get("/permissions")
def get_policy_permissions(user: UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:
    "Which actions the current user may use on the policies. The frontend shows or hides the buttons with it."
    is_admin = user.role >= UserRolesEnum.ADMIN

    return PermissionResponseModel(user_tag = user.tag,
                                   role = user.role,
                                   insert = is_admin,
                                   delete = is_admin,
                                   edit = is_admin)