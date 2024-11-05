from typing import Any, Dict, List, Type

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

import lib.data as dlib
import lib.data.sql.postgresql as psql

from lib.rest.security import RestPermissionSteward, RestSessionInformation

from config import get_system_settings

router = APIRouter(prefix="/api", tags=["User"])

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
def rest_get_query_user(query : str = None, max_users : int = 40,  # Fixme: rewrite method, clean up, better query function!
                        session: RestSessionInformation = Depends(RestPermissionSteward())):
    db_users: Type[dlib.ABCUser] = dlib.ABCUser.get_class()
    all_usernames = db_users.get_user_names()

    # ToDo: Implement filter that searches additional fields (see todo above), using db_users.get_users() above
    # u for u in users if any(q.lower() in getattr(u, p)
    filtered_usernames = [username for username, user_id in all_usernames.items() if username.lower().find("superuser") >= 0]

    us: Type[dlib.ABCUser] = dlib.ABCUser.get_class()
    users: List[dlib.ABCUser] = []
    filtered_users: List[Dict[str, Any]] = []
    # ToDo: Add new function to dlib.ABCUser (objectify with usernames or ids)

    for username in filtered_usernames:
        user = dlib.ABCUser.objectify_with_username(username = username)
        filtered_users.append({"id": user.get_id(),  # ToDo: Short list for security reason, counter check what properties are required from Frontend
                               "label": user.get_username(),  # Deprecated, use username
                               "username": user.get_username(),  # Deprecated
                               "firstname": user.get_firstname(),
                               "lastname": user.get_lastname(),
                               "research_group_id": user.get_research_group().get_id() if user.get_research_group() else None,
                               "research_group": user.get_research_group().get_name() if user.get_research_group() else None,
                               "institute": user.get_research_group().get_institute() if user.get_research_group() else None})

    # ToDo: Create PRM for rest_query_user
    # Question: Rule to have PRM?
    return {"users" : filtered_users,  # ToDo: Check if every item a dictionary in the old code
            "user_labels" : filtered_usernames,
            "query_count" : len(filtered_usernames),
            "total_count" : len(all_usernames)}

@router.get("/users/public")  # response_model=CollaboratorsResponseModel) # ToDo Implement PRM
def rest_get_user_list(session: RestSessionInformation = Depends(RestPermissionSteward())):
    """
    Returns collaborators, which is essential Users with a different response model (e.g. non sensitive information.)
    The response model defines the information that the API returns
    """
    u: dlib.ABCUser = dlib.ABCUser.get_class()

    return {"users": [{"label": username,  # Deprecated: use username instead
                       "username": user.get_username(),
                       "firstname": user.get_firstname(),
                       "lastname": user.get_lastname(),
                       "research_group": user.get_research_group().get_name() if user.get_research_group() else "None",
                       "institute": user.get_research_group().get_institute() if user.get_research_group() else "None",
                       "email": user.get_email()} for username, user in u.get_users(usernames=None).items()]}

