from fastapi.security import  OAuth2PasswordRequestForm
from fastapi import Depends

from services.encryption import verify_password, get_decoded_token
from config.exceptions.HTTPExceptions import user_form_data_incorrect, credentials_exception, user_blocked, user_role_too_low, token_not_valid_exception
from config.models.user import User, UserRolesEnum

from lib.user.UserHandling import UserDB

def get_user_from_login(form_data : OAuth2PasswordRequestForm = Depends()) -> User:
    """Returns the user from a login"""
    
    user_exists, user_in_db  = UserDB.get_user_by_email(form_data.username)
    #user verification check
    user_in_db = check_user_allowed(user_exists,user_in_db)
   
    if not verify_password(form_data.password, user_in_db.password.get_secret_value()):
        raise credentials_exception
    return user_in_db


def check_user_allowed(user_exists, user : User) -> User:
    """Checks if user is allowed to login"""
    if not user_exists:
        raise user_form_data_incorrect
    if not user.allow_login:
        raise user_blocked
    
    return user 


def get_user_from_token(token = Depends(get_decoded_token)) -> User:
    """Extracts the user from a token"""
    #DB.get_user_by_id()
    if "label" not in token : token_not_valid_exception
    user_exists, user_in_db = UserDB.get_user_by_label(token["label"])
    user  = check_user_allowed(user_exists,user_in_db)
    return user 

def is_user_at_least_curator(user : User = Depends(get_user_from_token)) -> User:
    """Checks if the user is at least curator.
    raises an exception if the userrole is not at least curator."""
    if (user.role >= UserRolesEnum.CURATOR):
        return user
    raise user_role_too_low

def is_user_admin(user : User = Depends(get_user_from_token)) -> User:
    """Checks if the user is at least admin.
    raises an exception if the userrole is not admin."""
    if (user.role >= UserRolesEnum.ADMIN):
        return user
    raise user_role_too_low
