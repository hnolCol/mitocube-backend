from typing import Any, Dict, List, Type
import warnings

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

import lib.data as dlib
import lib.data.sql.postgresql as psql

from lib.rest.security import rest_verify_user_token, RestSessionInformation

from config import get_system_settings


router = APIRouter(prefix="/api", tags=["User"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)

# ToDo: Next routes
# @router.post("/users", summary="Add a new user to the database.")
# @router.post("/users/pw",summary="Allows users to change the password for themselves.")
# @router.patch("/users/user", summary="Updates some properties of a user")
# @router.get("/users/full",  response_model=UsersAdminResponse)
# @router.get("/users/public", response_model=CollaboratorsResponseModel)
# @router.get("/users/roles", summary="Returns the available user roles and names", response_model=UseRoleReponseModel)
# @router.get("/users/{user_label}", summary="Returns the public user information of a user by its label.", response_model=PublicUser)
# @router.delete("/users/{user_label}", summary="Deletes a user. Requires admin rights.")
# @router.post("/users/user/block", summary="Block a user. Requires admin rights.")
# @router.post("/users/{user_label}/useterms", summary="Accept useterms. Can only be done by the user itself.")

@router.get("/users/q")  # Question: Where is this called?
def rest_get_query_user(query : str = None, max_users : int = 40,
                        session: RestSessionInformation = Depends(rest_verify_user_token)):
    db_users: Type[dlib.ABCUser] = dlib.ABCUser.get_class()
    usernames = db_users.get_user_names()

    # ToDo: Implement filter that searches additional fields (see todo above), using db_users.get_users() above
    # u for u in users if any(q.lower() in getattr(u, p)
    filtered_usernames = [username for username in usernames if username.lower().find(query.lower())]

    # ToDo: Create PRM for rest_query_user
    # Question: Rule to have PRM?
    return {"users" : filtered_usernames,  # ToDo: Check if every item a dictionary in the old code
            "user_labels" : filtered_usernames,
            "query_count" : len(filtered_usernames),
            "total_count" : len(usernames)}

@router.get("/users/public")  # response_model=CollaboratorsResponseModel) # ToDo Implement PRM
def test_get_user_list(session: RestSessionInformation = Depends(rest_verify_user_token)):
    """
    Returns collaborators, which is essential Users with a different response model (e.g. non sensitive information.)
    The response model defines the information that the API returns
    """
    u: dlib.ABCUser = dlib.ABCUser.get_class()

    return {"users": [{"label": username,  # Deprecated: use username instead
                       "username": user.get_username(),
                       "firstname": user.get_firstname(),
                       "lastname": user.get_lastname(),
                       "research_group": user.get_research_group().get_name() if user.get_research_group() else None,
                       "institute": user.get_research_group().get_institute() if user.get_research_group() else None,
                       "email": user.get_email()} for username, user in u.get_users(usernames=None).items()]}


@router.get("/users/roles", summary="Returns the available user roles and names")  #, response_model=UseRoleReponseModel)
def rest_get_user_roles(session: RestSessionInformation = Depends(rest_verify_user_token)):  # deprecated: rest_get_user_roles
    # user : UserModel = Depends(get_user_from_token)):
    """Returns the user role enumerator."""
    # ToDo: Figure out what to return here? list/dict of possible roles? Replace with permission definitions
    # ToDo: Create ABCPermissionGroups and link it with ABCUser, sql table sec_nm_permission_users and sec_permission_groups
    return {"GUEST": 0, "STANDARD": 1, "CURATOR": 2, "ADMIN": 4}


@router.get("/attributes/user")  # , response_model=AttributeResponseModel)  # Deprecated: rest_get_user_attributes!
def rest_get_user_attributes(session: RestSessionInformation = Depends(rest_verify_user_token)):  # deprecated: rest_get_user_attributes
    deprecated_api("/api/attributes/user -> lib.rest.routes.users.[users.py].rest_get_user_attributes()")
    user = session.get_user()
    # ToDo: Replace with simple dictionary structure
    # Question: Does not return profile but possible options for affiliation?
    # Before
    # {attributes: List[AttributeModel], attribute_values: List[AttributeValueModel]}
    # Suggesting just a dict with fields for the profile. Currently just mock data, not sure how it really works front end wise.
    # ToDo: Below does not match the Frontent at all, fix it or fix the gui?
    return {"attributes": [{"id": -1, "tag": "ratt_usernames", "text": "Usernames"},
                           {"id": -4, "tag": "ratt_contact", "text": "Contact Details"},
                           {"id": -5, "tag": "ratt_base64_image", "text": "Image"},
                           {"id": -7, "tag": "ratt_profile", "text": "Profile Information"}],
            "attribute_values": [{"id": -14, "attribute_id": -1 , "tag": "ratt_username:user", "text": "Username", "value": user.get_username()},
                                 {"id": -15, "attribute_id": -1 , "tag": "ratt_username:first", "text": "First Name", "value": user.get_firstname()},
                                 {"id": -16, "attribute_id": -1 , "tag": "ratt_username:last", "text": "Last Name", "value": user.get_lastname()},
                                 {"id": -17, "attribute_id": -4, "tag": "ratt_contact:email", "text": "Contact eMail", "value": user.get_email()},
                                 {"id": -18, "attribute_id": -5 , "tag": "ratt_base64_image:profile", "text": "Profile Image", "value": user.get_base64_image()},
                                 {"id": -18, "attribute_id": -7, "tag": "ratt_profile:orcid", "text": "ORCiD", "value": user.get_orcid() if user.get_orcid() else "None"},
                                 {"id": -19, "attribute_id": -7, "tag": "ratt_profile:url", "text": "URL", "value": user.get_url() if user.get_url() else "None"},
                                 {"id": -20, "attribute_id": -7, "tag": "ratt_profile:profile_text", "text": "Profile", "value": user.get_profile_text()},
                                 {"id": -21, "attribute_id": -7, "tag": "ratt_profile:research_group", "text": "Research Group", "value": user.get_research_group().get_name() if user.get_research_group() else "No Reserach Group"},
                                 {"id": -22, "attribute_id": -7, "tag": "ratt_profile:expires_after", "text": "Profil expires after", "value": user.get_expires_after()},
                                 {"id": -22, "attribute_id": -7, "tag": "ratt_profile:last_login", "text": "Research Group", "value": user.get_last_login_on()}]}
