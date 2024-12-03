from typing import Any, Annotated, Dict
import re

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Header, status, Request
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from config import SystemSettings

from lib.rest.security import RestPermissionSteward, RestSessionInformation

import lib.data as dlib
from lib.data.mem import MemLoginToken, MemLoginTokens, MemLoginTokenError
from lib.data.mem import MemUserToken, MemUserTokens, MemUserTokenError
import lib.data.sql.postgresql as psql
from lib.io.com import EMailHandler


router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login/", tags = ["Login"])
def rest_post_request_email_login_token(background_task: BackgroundTasks,
                                        request: Request,
                                        user_agent: Annotated[str | None, Header()] = None,
                                        form_data: OAuth2PasswordRequestForm = Depends()):
    user: dlib.ABCUser

    try:
        if re.search("^[a-zA-Z0–9._%+-]+@[a-zA-Z0–9.-]+\\.[a-zA-Z]{2,}$", form_data.username):
            user = psql.PostgreSQLUser.objectify_with_email(email=form_data.username)
        else:
            user = psql.PostgreSQLUser.objectify_with_username(username=form_data.username)
    except dlib.ABCUserError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.")
                            # headers={"WWW-Authenticate": "Bearer"})  # Question, what was that for?

    try:
        user.login(password=form_data.password)
    except dlib.ABCUserError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.")
                            # headers={"WWW-Authenticate": "Bearer"})  # Question, what was that for?

    db_login_tokens = MemLoginTokens()
    verification_code: str = db_login_tokens.create_token(username=user.get_username(),
                                                          ip=request.client.host,
                                                          agent=user_agent if user_agent else "None")

    print("> Send the code '{code}' to '{email}'.".format(email=user.get_email(),
                                                          code=verification_code, ))  # Fixme: Remove this line after debugging!!!

    system_settings = SystemSettings.get_system_settings()
    EMailHandler.send_email_in_background(background_tasks=background_task,
                                          subject="Token Verification",  # ToDo: Move to configuration
                                          email_to=[user.get_email()],
                                          include_setting_cc=False,
                                          body={"app_name": system_settings.app_name,
                                                "first_name": user.get_lastname(),
                                                "verification_code": verification_code},
                                          template_name=system_settings.mail_template_verification)


@router.post("/login/validate/", tags = ["Login"])
def rest_post_validate_login_token(request: Request,
                                   token_to_verify: str = Form(),
                                   user_agent: Annotated[str | None, Header()] = None):
    login_token: MemLoginToken

    db_login_tokens = MemLoginTokens()

    try:
        login_token = db_login_tokens.test_token(token = token_to_verify,
                                                 ip = request.client.host,
                                                 agent = user_agent if user_agent else "None")
    except MemLoginTokenError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user login.")
                            # headers={"WWW-Authenticate": "Bearer"})  # Question, what was that for?

    db_login_tokens.remove_token(login_token)

    db_session_tokens = MemUserTokens()
    token_session: str = db_session_tokens.create_token(username = login_token.get_username(),
                                                        ip = request.client.host,
                                                        agent = user_agent if user_agent else "None")
    db_session_tokens._write()  # Fixme, remove or find a solution to do it with shut down signal (close needs then also to remove everything in memory!)

    return {"token": token_session, "username": login_token.get_username()}

@router.get("/login/username/")
def rest_get_username(session: RestSessionInformation = Depends(RestPermissionSteward())):
    return {"username": session.get_token().get_username()}

@router.get("/logout/", tags = ["Logout"])
def rest_get_logout(session: RestSessionInformation = Depends(RestPermissionSteward())):
    db_user_tokens = MemUserTokens()
    token: MemUserToken = session.get_token()

    db_user_tokens.remove_token(token = token)
