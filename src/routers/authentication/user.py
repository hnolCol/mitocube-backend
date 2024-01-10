from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException
from typing import List 
from config.exceptions.HTTPExceptions import user_role_too_low
from config.settings.email import get_email_settings
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel, CollaboratorsResponseModel, UsersAdminResponse, UserModelForRegistration, UserLabel, UserModelForUpdate, UseRoleReponseModel
from services.encryption import decode_token
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from services.enums import get_enum_as_dict
from lib.user.UserHandling import UserDB
from config.settings.general import get_general_settings

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()

router = APIRouter(
    prefix="/api",
    tags=["Token", "Authentication","UserModel"]
    )



@router.post("/users/user", summary="Add a new user.")
def add_user_to_the_database(background_task : BackgroundTasks, user_props : dict, user : UserModel = Depends(is_user_admin)):
    """
    Adds a user to the database. Currently requires admin rights.
    """
    #TO DO: should find another solution for this renmaing, also in patch 
    user_props_att_renamed = dict([(k.replace("att_user_",""), v if not isinstance(v, dict) else v["name"]) for k,v in user_props.items()])
    try:
        user_to_add = UserModelForRegistration(**user_props_att_renamed)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=422,detail=str(e))
    UserDB.add_user(user_props=user_to_add) #throws ane exception if there is a problem

    send_email_in_background(background_tasks=background_task,
                             subject="Account generated.",
                             email_to=[user_to_add.email],
                             include_setting_cc=False, #do not include the setting based ccs
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : user_to_add.firstname,
                                 "password" : user_to_add.password
                             },
                             template_mame=EMAIL_SETTINGS.mail_account_generated_template)


@router.patch("/users/user", summary="Updates some properties of a user")
def update_user(user_props : dict, user : UserModel = Depends(is_user_admin)):
    """Requires admin rights. Change to allow that users modify themselves."""
    print(user_props)
    user_props_att_renamed = dict([(k.replace("att_user_",""), v if not isinstance(v, dict) else v["name"]) for k,v in user_props.items()])
    try:
        user_to_update = UserModelForUpdate(**user_props_att_renamed)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=422,detail=str(e))
        
    UserDB.update_user_by_label(user_label = user_to_update.label, user_props=user_to_update)
    



@router.get("/users/full",  response_model=UsersAdminResponse)
def get_users(user : UserModel = Depends(is_user_admin)):
    """
    Returns a list of users, requires admin rights.
    Full indicates that the full information of a user is provided.
    """
    users = UserDB.get_users()
    return {"users" : users}


@router.get("/users/public", response_model=CollaboratorsResponseModel)
def get_collaborators(user : UserModel = Depends(get_user_from_token)):
    """
    Returns collaborators, which is essential Users with a different response model (e.g. non sensitive information.)
    The response model defines the information that the API returns
    """
    users = UserDB.get_users()
    return {"users" : users}


@router.get("/users/roles", summary="Returns the available user roles and names", response_model=UseRoleReponseModel)
def get_user_roles(user : UserModel = Depends(get_user_from_token)):
    """Returns the user role enumerator."""
    return UseRoleReponseModel()


@router.delete("/users/{user_label}", summary="Deletes a user. Requires admin rights.")
def delete_user(user_label : str, user : UserModel = Depends(is_user_admin)):
    """Deletes specific user. Returns an error if token does not belong to admin"""
    UserDB.delete_user_by_label(user_label)

## inconsistent!  - change

@router.post("/users/user/block", summary="Block a user. Requires admin rights.")
def block_user(user_props : UserLabel, user : UserModel = Depends(is_user_admin)):
    """Blocks the user. Limited to admin users."""
    UserDB.block_user_by_label(user_props.label)

# @router.post("/")
# def add_user(user : UserModel = Depends(is_user_admin)):
#     """
#     """

#     return {}


# @router.get("/{user_id}")
# def get_user_by_id():
#     """
#     Returns a user by the user id.
#     Requires admin rights
#     """

#     return {}

# @router.get("/{user_email}")
# def get_user_by_email():
#     """
#     Returns an user by its email
#     """

#     return {}