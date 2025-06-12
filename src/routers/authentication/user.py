from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException
from typing import List, Dict
from config.exceptions.HTTPExceptions import user_role_too_low, user_not_found
from config.settings.email import get_email_settings
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel, CollaboratorsResponseModel, UsersAdminResponse, UserModelForRegistration, UserLabel, UserModelForUpdate, UseRoleReponseModel, AddUserPropsModel, PublicUser
from config.models.parameter import APIParamString
from services.encryption import decode_token
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from services.enums import get_enum_as_dict
from lib.user.UserHandling import UserDB
from config.settings.general import get_general_settings
from lib.database.Database import Database
DB = Database.DB()
EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()

router = APIRouter(
    prefix="/api",
    tags=["Token", "Authentication","UserModel"]
    )



@router.get("/users",summary="Returns the user tags in the database")
def get_user_tags(limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    return DB.users.get_tags(limit=limit)


@router.post("/users", summary="Add a new user to the database.")
def add_user_to_the_database(background_task : BackgroundTasks, user_props : AddUserPropsModel, user : UserModel = Depends(is_user_admin)):
    """
    Adds a user to the database. Currently requires admin rights.
    """
    #user_props = AddUserPropsModel(**user_props)
    #TO DO: should find another solution for this renmaing, also in patch 
    user_props = user_props.model_dump(exclude_none=True)
    try:
        user_to_add = UserModelForRegistration(**user_props )
    except Exception as e:
        raise HTTPException(status_code=422,detail=str(e))
    try:
        DB.users.add_user(user_to_add)
    except ValueError as e:
        raise HTTPException(status_code=500, detail = str(e))
        return 
    
    #UserDB.add_user(user_props=user_to_add) #throws ane exception if there is a problem

    send_email_in_background(background_tasks=background_task,
                             subject="Account generated.",
                             email_to=[user_to_add.email],
                             include_setting_cc=False, #do not include the setting based ccs
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : user_to_add.firstname,
                                 "password" : user_to_add.password,
                                 "url" : GENERAL_SETTINGS.url
                             },
                             template_mame=EMAIL_SETTINGS.mail_account_generated_template)


@router.get("/users/q")
def query_user_db(query : str = None, max_users : int = 40, user : UserModel = Depends(get_user_from_token)):
    """Query user in the database. 

    Parameters
    ----------
    query : str, optional
        _description_, by default None
    max_users : int, optional
        _description_, by default 40

    Returns
    -------
    _type_
        _description_
    """
    
    filtered_users = DB.users.find_user(query, limit=max_users)
    total_count = DB.users.count()
    query_count = len(filtered_users)
   
    return {"users" : filtered_users, 
            "user_tags" : [u.tag for u in filtered_users], 
            "query_count" : query_count, 
            "total_count" : total_count} 

@router.post("/users/pw",summary="Allows users to change the password for themselves.")
def change_password(updated_pw : Dict[str,str], user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    updated_pw : Dict
        A dict of shape updated_pw = {"password" : <string>}.
    user : UserModel, optional
        The User identified using the jwt token, by default Depends(get_user_from_token)

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    HTTPException
        _description_
    """
    try:
        UserDB.update_user_password_by_label(user_label=user.label, password = updated_pw["password"])
    except Exception as e:
        raise HTTPException(status_code=400,detail="An error occurred during password change.")
    
@router.patch("/users/user", summary="Updates some properties of a user")
def update_user(user_props : dict, user : UserModel = Depends(is_user_admin)):
    """Requires admin rights. Change to allow that users modify themselves."""
    user_props_att_renamed = dict([(k.replace("att_user_",""), v if not isinstance(v, dict) else v["name"]) for k,v in user_props.items()])
    try:
        user_to_update = UserModelForUpdate(**user_props_att_renamed)
    except Exception as e:
        raise HTTPException(status_code=422,detail=str(e))
        
    UserDB.update_user_by_label(user_label = user_to_update.label, user_props=user_to_update)
    

@router.get("/users/full",  response_model=UsersAdminResponse)
def get_users(user : UserModel = Depends(is_user_admin)):
    """
    Returns a list of users, requires admin rights.
    Full indicates that the full information of a user is provided.
    """
    users = DB.users.get_users()
    return {"users" : users}



@router.get("/users/public", response_model=List[PublicUser])
def get_collaborators(tags : str = None, user : UserModel = Depends(get_user_from_token)):
    """
    Returns collaborators, which is essential Users with a different response model (e.g. non sensitive information.)
    The response model defines the information that the API returns
    """
    return DB.users.get_users_by_tags(tags=APIParamString(param=tags).param)
    


@router.get("/users/roles", summary="Returns the available user roles and names", response_model=UseRoleReponseModel)
def get_user_roles(user : UserModel = Depends(get_user_from_token)):
    """Returns the user role enumerator."""
    return UseRoleReponseModel()


@router.get("/users/{user_tag}", summary="Returns the public user information of a user by its label.", response_model=PublicUser)
def get_user(user_tag : str, user : UserModel = Depends(get_user_from_token)):
    """Deletes specific user. Returns an error if token does not belong to admin"""
    user_from_db = DB.users.get_user_by_tag(user_tag)
    if user_from_db is None : raise user_not_found
    return user_from_db


@router.delete("/users/{user_tag}", summary="Deletes a user. Requires admin rights.")
def delete_user(user_tag : str, user : UserModel = Depends(is_user_admin)):
    """Deletes specific user. Returns an error if token does not belong to admin"""    
    

## inconsistent!  - change to have user_label in url 

@router.post("/users/{user_tag}/block", summary="Block a user. Requires admin rights.")
def block_user(user_tag : str, user : UserModel = Depends(is_user_admin)):
    """Blocks the user. Limited to admin users."""
    DB.users.block_user_by_tag(tag = user_tag)
    #UserDB.block_user_by_label(user_props.label)
    
    
@router.post("/users/{user_label}/useterms", summary="Accept useterms. Can only be done by the user itself.")
def accept_use_terms(user_label : str, accept : bool, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    user_label : str
        _description_
    accept : bool
        _description_
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)
    """
    #TODO add functionality to UserDB.

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