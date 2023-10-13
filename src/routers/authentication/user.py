from fastapi import APIRouter, Depends, Request
from typing import List 
from config.enums.users.roles import UserRolesEnum
from config.models.user import User, Collaborators, UsersAdminResponse
from services.encryption import decode_token
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from services.enums import get_enum_as_dict
from lib.user.UserHandling import UserDB


router = APIRouter(
    prefix="/api",
    tags=["Token", "Authentication","User"]
    )


@router.get("/users/full",  response_model=UsersAdminResponse)
def get_users(user : User = Depends(is_user_admin)):
    """
    Returns a list of users, requires admin rights.
    Full indicates that the full information of a user is provided.
    """
    users = UserDB.get_users()
    return {"users" : users}


@router.get("/users/public", response_model=Collaborators)
def get_collaborators(user : User = Depends(get_user_from_token)):
    """
    Returns collaborators, which is essential Users with a different response model (e.g. non sensitive information.)
    The response model defines the information that the API returns
    """
    users = UserDB.get_users()
    return {"users" : users}




# @router.post("/")
# def add_user(user : User = Depends(is_user_admin)):
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