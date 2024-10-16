from typing import Annotated, Tuple

from fastapi import Header, status, Request
from fastapi.exceptions import HTTPException


import lib.data as dlib
from lib.data.mem import MemUserToken, MemUserTokens, ABCUserTokenError
import lib.data.sql.postgresql as psql


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


def rest_verify_user_login():
    pass  # ToDo: Implement rest_verify_user_login()

def rest_verify_login_token():
    pass  # ToDo: Implement rest_verify_login_token()

def rest_verify_admin_token(request: Request,
                            user_agent: Annotated[str | None, Header()] = None) -> RestSessionInformation:
    user, token, token_obj = verify_user_token(request = request, user_agent = user_agent)

    if user.get_username() not in ("superuser"):  # ToDo: Implement it using permission groups, or use config...
        raise HTTPException(status_code=status.HTTP_403_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="You require admin rights to proceed.",
                            headers={"WWW-Authenticate": "Bearer"})

    return RestSessionInformation(user = user,  # dlib.ABCUser
                                  token = token_obj,  # MemUserToken
                                  ip = request.client.host,  # str
                                  agent = user_agent if user_agent else "None")

def rest_verify_user_token(request: Request,
                           user_agent: Annotated[str | None, Header()] = None) -> RestSessionInformation:
    user, token, token_obj = verify_user_token(request = request, user_agent = user_agent)

    return RestSessionInformation(user = user,  # dlib.ABCUser
                                  token = token_obj,  # MemUserToken
                                  ip = request.client.host,  # str
                                  agent = user_agent if user_agent else "None")


def verify_user_token(request: Request,
                      user_agent: Annotated[str | None, Header()] = None) -> Tuple[dlib.ABCUser, str, MemUserToken]:
    user: dlib.ABCUser
    token: str
    db_session_tokens = MemUserTokens()

    if "authorization" in request.headers.keys():
        token = request.headers["authorization"].replace("Bearer ", "")  # Question: Better way? Look at Auth and Session middle ware?
    else:
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user session.",
                            headers={"WWW-Authenticate": "Bearer"})

    try:
        token_obj = db_session_tokens.test_token(token = token,
                                                 ip = request.client.host,
                                                 agent = user_agent if user_agent else "None")
    except ABCUserTokenError as err:
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user session.",
                            headers={"WWW-Authenticate": "Bearer"})

    if token_obj.is_expired():
        # Question: Log message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user session.",
                            headers={"WWW-Authenticate": "Bearer"})
    elif token_obj.get_ip() != request.client.host:
        # Question: Log message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user session.",
                            headers={"WWW-Authenticate": "Bearer"})
    elif token_obj.get_agent() != user_agent if user_agent else "None":
        # Question: Log message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user session.",
                            headers={"WWW-Authenticate": "Bearer"})

    try:
        user = psql.PostgreSQLUser.objectify_with_username(username=token_obj.get_username())
    except dlib.ABCUserError as err:  # ToDo: Implement ABCUserNotExistError(ABCUserError) and similar everywhere
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Unable to verify token provided for user session.",
                            headers={"WWW-Authenticate": "Bearer"})

    return user, token, token_obj
