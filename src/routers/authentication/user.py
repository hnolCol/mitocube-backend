from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException
from typing import List, Dict
from config.exceptions.HTTPExceptions import user_role_too_low, user_not_found
from config.settings.email import get_email_settings
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel, CollaboratorsResponseModel, UsersAdminResponse, UserModelForRegistration, UserLabel, UserModelForUpdate, UseRoleReponseModel, AddUserPropsModel, PublicUser, UserCreateModel, UserInsertModel
from config.models.parameter import APIParamString
from services.encryption import verify_password
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from services.enums import get_enum_as_dict

from config.settings.general import get_general_settings
from config.models.news.news import NewsInsertModel
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
def add_user_to_the_database(background_task : BackgroundTasks, user_props : UserCreateModel, user : UserModel = Depends(is_user_admin)):
    """
    Adds a user to the database. Currently requires admin rights.
    """

    tag = DB.users.get_new_tag() 
    plain_pw = DB.users.create_plain_password() 
    hashed_pw = DB.users.hash_password(plain_pw)
    user_props = UserInsertModel(**user_props.model_dump(), tag=tag, password=hashed_pw)
    ok = DB.users.insert(user_props)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert user in the database.")

    send_email_in_background(background_tasks=background_task,
                             subject="Account generated.",
                             email_to=[user_props.email],
                             include_setting_cc=False, #do not include the setting based ccs
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : user_props.firstname,
                                 "password" : plain_pw,
                                 "url" : GENERAL_SETTINGS.url
                             },
                             template_name=EMAIL_SETTINGS.mail_account_generated_template)
    
    DB.news.insert(NewsInsertModel(content=f"{user_props.firstname} {user_props.lastname} joined the MitoCube. Welcome!.", title="New user", user_tag=tag))



@router.get("/users/count", summary="Returns the number of users in the database.")
def count_user_db(exclude_inactive : bool = True, user : UserModel = Depends(get_user_from_token)) -> int:
    """Returns the number of users in the database.
    
    Parameters
    ----------
    exclude_inactive : bool, optional   
        If True, inactive users are not counted, by default True
        
    Returns     
    -------
    int
        The number of users in the database.
    """
    return DB.users.count(exclude_inactive=exclude_inactive)

@router.get("/users/q")
def query_user_db(search_string : str = None, limit : int = 40, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    """Query user in the database and returns the tags 

    Parameters
    ----------
    query : str, optional
        _description_, by default None
    limit : int, optional
        _description_, by default 40

    Returns
    -------
    _type_
        _description_
    """

    return DB.users.find(search_string, limit=limit)

# @router.post("/users/pw",summary="Allows users to change the password for themselves.")
# def change_password(updated_pw : Dict[str,str], user : UserModel = Depends(get_user_from_token)):
#     """_summary_

#     Parameters
#     ----------
#     updated_pw : Dict
#         A dict of shape updated_pw = {"password" : <string>}.
#     user : UserModel, optional
#         The User identified using the jwt token, by default Depends(get_user_from_token)

#     Returns
#     -------
#     _type_
#         _description_

#     Raises
#     ------
#     HTTPException
#         _description_
#     """
#     # try:
#     #     UserDB.update_user_password_by_label(user_label=user.label, password = updated_pw["password"])
#     # except Exception as e:
#     #     raise HTTPException(status_code=400,detail="An error occurred during password change.")

#     new_password = updated_pw.get("password")
#     if not new_password:
#         raise HTTPException(422, "Password is required.")

#     try:
#         hashed = DB.users.hash_password(new_password)
#     except ValueError as e:
#         raise HTTPException(422, str(e))

#     if not DB.users.update(tag=user.tag, user_props={"password": hashed}):
#         raise HTTPException(400, "Could not update password.")
    
@router.post("/users/pw", summary="Allows users to change the password for themselves.")
def change_password(updated_pw: Dict[str, str], user: UserModel = Depends(get_user_from_token)):
    """Change the authenticated user's password."""
    old_password = updated_pw.get("old_password")
    new_password = updated_pw.get("password")

    if not old_password or not new_password:
        raise HTTPException(422, "Old and new password are required.")
    if old_password == new_password:
        raise HTTPException(422, "New password must be different from the current password.")

    db_user = DB.users.get_user_by_tag(user.tag)
    if db_user is None or db_user.password is None:
        raise HTTPException(404, "User not found.")

    if not verify_password(old_password, db_user.password.get_secret_value()):
        raise HTTPException(401, "Current password is incorrect.")

    try:
        hashed = DB.users.hash_password(new_password)
    except ValueError as e:
        raise HTTPException(422, str(e))

    if not DB.users.update(tag=user.tag, user_props={"password": hashed}):
        raise HTTPException(400, "Could not update password.")
    

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
    

@router.get("/users/roles/{user_tag}", summary="Returns the roles of a user by its tag.", response_model=int)
def get_user_role(user_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    """Returns the role of a user by its tag."""
    return user.role 


@router.get("/users/{user_tag}/submissions/count", summary="Returns the number of submissions of a user by its tag.")
def count_user_submissions(user_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    """Counts the number of submissions for a user by its tag."""
    if not DB.users.exists(tag = user_tag): raise user_not_found
    return len(DB.submission_filter.filter_by_user(user_tags=[user_tag]))

## inconsistent!  - change to have user_label in url 

@router.post("/users/{user_tag}/block", summary="Block a user. Requires admin rights.")
def block_user(user_tag : str, user : UserModel = Depends(is_user_admin)):
    """Blocks the user. Limited to admin users."""
    DB.users.block_user_by_tag(tag = user_tag)
    #UserDB.block_user_by_label(user_props.label)
    
    
@router.get("/users/{user_tag}/exists", summary="Checks if a user exists by its tag.")
def check_if_user_exists(user_tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
    """Checks if a user exists by its tag."""
    return DB.users.exists(tag = user_tag)

@router.get("/users/{user_tag}/is_active", summary="Checks if a user is active by its tag.")
def check_if_user_is_active(user_tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
    """Checks if a user is active by its tag."""
    return DB.users.is_user_active(tag = user_tag)

    
    
@router.post("/users/{user_tag}/useterms", summary="Accept useterms. Can only be done by the user itself.")
def accept_use_terms(user_tag : str, accept : bool, user : UserModel = Depends(get_user_from_token)):
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
