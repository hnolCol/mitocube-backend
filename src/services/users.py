from fastapi.security import  OAuth2PasswordRequestForm
from fastapi import Depends
from pydantic import EmailStr
from typing import List, Tuple
from services.encryption import verify_password, get_decoded_token
from config.exceptions.HTTPExceptions import user_form_data_incorrect, credentials_exception, user_blocked, user_role_too_low, token_not_valid_exception
from config.models.user import UserModel, UserRolesEnum, PublicUser

from lib.user.UserHandling import UserDB
from lib.database.Database import Database
DB = Database.DB()


def are_public_users_allowed(user_tags  : List[str]) -> List[bool]:
    """Checks if a list of Users are allowed to login."""
    #user_tags = [u.tag for u in users]
    users_from_db = DB.users.get_users_by_tags(tags = user_tags)
    return [u.allow_login for u in users_from_db if u is not None]

def get_user_from_login(form_data : OAuth2PasswordRequestForm = Depends()) -> UserModel:
    """Returns the user from a login"""
    user  = DB.users.get_user_by_email(form_data.username)
    #user verification check
    user_in_db = check_user_allowed(user is not None,user)

    if not verify_password(form_data.password, user_in_db.password.get_secret_value()):
        raise credentials_exception
    return user_in_db

def check_user_allowed(user_exists : bool, user : UserModel) -> UserModel:
    """
    Checks if user is allowed to login
    
    Parameters
    ----------
    user_exists : bool 
        If the user exists. 
    user : UserModel 
        The user to check

    Returns
    -------
    UserModel
        The user if checks are passed, otherwise raises an HTTP Exception. 

    Raises
    ------
        HTTP Exception 
            if user form data is incorrect
        HTTP Exception
            if user param allow_login is False 
    """
    if not user_exists:
        raise user_form_data_incorrect
    if not user.allow_login:
        raise user_blocked
    return user 

def check_token_verified(token : str =  Depends(get_decoded_token)) -> str:
    """"""
    if "verified" in token and token["verified"]:
        return token 
    raise token_not_valid_exception

def get_user_from_token(token = Depends(check_token_verified)) -> UserModel:
    """Extracts the user from a token"""
    #DB.get_user_by_id()
    if "label" not in token : token_not_valid_exception
    user_in_db = DB.users.get_user_by_tag(tag = token["tag"])
    user  = check_user_allowed(user_in_db is not None,user_in_db)
    return user 

def is_user_at_least_curator(user : UserModel = Depends(get_user_from_token)) -> UserModel:
    """Checks if the user is at least curator.
    raises an exception if the userrole is not at least curator."""
    print(user)
    if (user.role >= UserRolesEnum.CURATOR):
        return user
    raise user_role_too_low

def is_user_admin(user : UserModel = Depends(get_user_from_token)) -> UserModel:
    """Checks if the user is at least admin.
    raises an exception if the userrole is not admin."""
    if (user.role >= UserRolesEnum.ADMIN):
        return user
    raise user_role_too_low
