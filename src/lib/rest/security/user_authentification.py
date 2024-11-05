from typing import Annotated, Tuple, List

import lib.data as dlib
from lib.data.mem import MemUserToken, MemUserTokens, ABCUserTokenError
import lib.data.sql.postgresql as psql

from fastapi import Header, status, Request
from fastapi.exceptions import HTTPException

class RestSessionInformation:
    def __init__(self, user: dlib.ABCUser | None, token: MemUserToken, ip: str, agent: str):
        self._user: dlib.ABCUser | None = user
        self._token: MemUserToken = token
        self._ip: str = ip
        self._agent: str = agent

    def get_agent(self) -> str:
        return self._agent

    def get_ip(self) -> str:
        return self._ip

    def get_user(self) -> dlib.ABCUser | None:
        return self._user

    def get_token(self) -> MemUserToken:
        return self._token

# Either test the following with (argument in FastAPI route definitions):
#
# check_superuser_permission = RestPermissionSteward(requires_users = ["superuser])
# ..., session: RestSessionInformation = Depends(check_superuser_permission), ...
#
# or directly:
#
# ..., session: RestSessionInformation = Depends(RestPermissionSteward(requires_users = ("superuser"))), ...
#
class RestPermissionSteward:  # Question: outsource RestPermissionSteward? ABCPermissionSteward PostgreSQLPermissionSteward and implement here the RestPermissionSteward?
    __superuser_name: str = "superuser"  # Question, is that sufficient? superuser should always generated with random password in install script that is send to an email at first access?

    def __init__(self, requires_users: Tuple[str] | None = None,  # only these users can access the route
                 requires_security_token: bool = True,  # User needs to be logged with session token or bot has key
                 requires_superuser: bool = False,  # alternative to requiring = ["superuser"]
                 require_permission_to_manage_system: bool = False,
                 require_permission_to_manage_attributes_traits: bool = False,
                 require_permission_to_manage_all_datasets: bool = False,
                 require_permission_to_manage_owned_datasets: bool = False,
                 require_permission_to_manage_instruments: bool = False,
                 require_permission_to_manage_genoytpes: bool = False,
                 require_permission_to_manage_features: bool = False,
                 require_permission_to_manage_research_groups: bool = False,
                 require_permission_to_manage_users: bool = False,
                 require_permission_to_submit_datasets: bool = False):  # Question, what other permission could be required?

        self._requires_users: Tuple[str] | None = requires_users  # ToDo: Implement Database link
        self._requires_security_token: bool = requires_security_token  # ToDo: _requires_security_token Not used yet. Requires ability to create session token if not exist and just proceed
        self._requires_superuser: bool = requires_superuser
        self._require_permission_to_manage_system: bool = require_permission_to_manage_system  # Todo: Implement Database link and Frontend to set below (also todo for lines below)
        self._require_permission_to_manage_attributes_traits: bool = require_permission_to_manage_attributes_traits
        self._require_permission_to_manage_all_datasets: bool = require_permission_to_manage_all_datasets
        self._require_permission_to_manage_owned_datasets: bool = require_permission_to_manage_owned_datasets
        self._require_permission_to_manage_instruments: bool = require_permission_to_manage_instruments
        self._require_permission_to_manage_genoytpes: bool = require_permission_to_manage_genoytpes
        self._require_permission_to_manage_features: bool = require_permission_to_manage_features
        self._require_permission_to_manage_research_groups: bool = require_permission_to_manage_research_groups
        self._require_permission_to_manage_users: bool = require_permission_to_manage_users
        self._require_permission_to_submit_datasets: bool = require_permission_to_submit_datasets

    def __call__(self, request: Request, user_agent: Annotated[str | None, Header()] = None) -> RestSessionInformation:
        user, token, token_obj = self.__verify_session(request=request, user_agent=user_agent)

        return RestSessionInformation(user=user,  # dlib.ABCUser
                                      token=token_obj,  # MemUserToken
                                      ip=request.client.host,  # str
                                      agent=user_agent if user_agent else "None")

    # Fixme, so far it is just mostly copied from the function 'verify_user_token', Implement it properly (extend database)
    def __verify_session(self, request: Request, user_agent: str | None = None) -> Tuple[dlib.ABCUser, str, MemUserToken]:
        user: dlib.ABCUser
        token: str
        db_session_tokens = MemUserTokens()

        if "authorization" in request.headers.keys():
            token = request.headers["authorization"].replace("Bearer ", "")
        else:
            # ToDo / Question: Log ABCLoginTokenError message?
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Unable to verify token provided for user session.",
                                headers={"WWW-Authenticate": "Bearer"})

        try:
            token_obj = db_session_tokens.test_token(token=token,
                                                     ip=request.client.host,
                                                     agent=user_agent if user_agent else "None")
        except ABCUserTokenError as err:
            # Question: Log ABCLoginTokenError message?
            # ToDo: Differentiate between TokenErrors? Implement ABCUserTokenExpiredError, etc.
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Unable to verify token provided for user session.",
                                headers={"WWW-Authenticate": "Bearer"})

        # The Following should be covered above
        # if token_obj.is_expired():
        #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        #                         detail="Unable to verify token provided for user session.",
        #                         headers={"WWW-Authenticate": "Bearer"})
        # elif token_obj.get_ip() != request.client.host:
        #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        #                         detail="Unable to verify token provided for user session.",
        #                         headers={"WWW-Authenticate": "Bearer"})
        # elif token_obj.get_agent() != user_agent if user_agent else "None":
        #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        #                         detail="Unable to verify token provided for user session.",
        #                         headers={"WWW-Authenticate": "Bearer"})

        try:
            user = psql.PostgreSQLUser.objectify_with_username(username=token_obj.get_username())
        except dlib.ABCUserError as err:  # ToDo: Implement ABCUserNotExistError(ABCUserError) and similar everywhere
            # Question: Log ABCLoginTokenError message?
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                                detail="Unable to verify token provided for user session.",
                                headers={"WWW-Authenticate": "Bearer"})

        if self._requires_superuser and user.get_username() != self.__superuser_name:
            raise HTTPException(status_code=status.HTTP_403_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                                detail="You do not have sufficient rights to proceed.",
                                headers={"WWW-Authenticate": "Bearer"})
        elif self._requires_users and user.get_username() not in self._requires_users:
            raise HTTPException(status_code=status.HTTP_403_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                                detail="You do not have sufficient rights to proceed.",
                                headers={"WWW-Authenticate": "Bearer"})

        return user, token, token_obj
