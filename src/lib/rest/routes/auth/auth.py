from typing import Annotated, Type
import re

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Header, status, Request
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from config import SystemSettings

from lib.rest.security import RestPermissionSteward, RestSessionInformation

import lib.data as dlib
from lib.io.com import EMailHandler


router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login/", tags = ["Login"])
def rest_post_request_email_login_token(background_task: BackgroundTasks,
                                        request: Request,
                                        user_agent: Annotated[str | None, Header()] = None,
                                        form_data: OAuth2PasswordRequestForm = Depends()):
    user: dlib.ABCUser
    user_db: Type[dlib.ABCUser] = dlib.ABCUser.get_class()
    error_message_401 = "Could not validate credentials. Invalid Token, User not found or password incorrect."  # Question: Move to config?

    try:
        if re.search("^[a-zA-Z0–9._%+-]+@[a-zA-Z0–9.-]+\\.[a-zA-Z]{2,}$", form_data.username):
            user = user_db.objectify_with_email(email=form_data.username)
        else:
            user = user_db.objectify_with_username(username=form_data.username)
    except dlib.ABCUserError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_message_401)
                            # headers={"WWW-Authenticate": "Bearer"})  # Question, what was that for?

    try:
        user.login(password=form_data.password)  # Also performs a user.is_login_allowed()
    except dlib.ABCUserError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_message_401)

    db_token: Type[dlib.ABCToken] = dlib.ABCToken.get_class()
    str_token: str
    token: dlib.ABCToken

    str_token, token = db_token.create(token_type = dlib.ABCTokenType.LOGIN,
                                       username = user.get_username(),
                                       ip = request.client.host,
                                       agent = user_agent if user_agent else "None")

    print("> Send the code '{token}' to '{email}'.".format(email = user.get_email(), token = str_token))  # Fixme: Remove this line after debugging!!!

    system_settings = SystemSettings.get_system_settings()
    EMailHandler.send_email_in_background(background_tasks = background_task,
                                          subject = "Token Verification",  # ToDo: Move to configuration
                                          email_to = [user.get_email()],
                                          include_setting_cc = False,
                                          body={"app_name": system_settings.app_name,
                                                "first_name": user.get_lastname(),
                                                "token": token},
                                          template_name = system_settings.mail_template_login_code)

@router.post("/login/validate/", tags = ["Login"])
def rest_post_validate_login_token(request: Request,
                                   token_to_verify: str = Form(),
                                   user_agent: Annotated[str | None, Header()] = None):

    db_token: Type[dlib.ABCToken] = dlib.ABCToken.get_class()
    login_token: dlib.ABCToken

    try:
        login_token = db_token.objectify_token(token = token_to_verify, token_type = dlib.ABCTokenType.LOGIN)
        login_token.test_token(token_type = dlib.ABCTokenType.LOGIN, agent = user_agent if user_agent else "None", ip = request.client.host)
    except dlib.ABCTokenError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to verify token provided for user login.")  # Question: Message to config?
                            # headers={"WWW-Authenticate": "Bearer"})  # Question, what was that for?

    db_token.remove_token(login_token)

    token_session, _ = db_token.create(token_type = dlib.ABCTokenType.LOGIN,
                                       username = login_token.get_username(),
                                       ip = request.client.host,
                                       agent = user_agent if user_agent else "None")

    return {"token": token_session, "username": login_token.get_username()}

@router.get("/username/")
def rest_get_username(session: RestSessionInformation = Depends(RestPermissionSteward())):
    return {"username": session.get_token().get_username()}

@router.get("/logout/", tags = ["Logout"])
def rest_get_logout(session: RestSessionInformation = Depends(RestPermissionSteward())):
    dlib.ABCToken.get_class().remove_token(token = session.get_token())

@router.get("/request_email_verification/{username}", tags=["Logout"])
def rest_get_request_verify_email(background_task: BackgroundTasks,
                                  request: Request,
                                  username: str,
                                  user_agent: Annotated[str | None, Header()] = None):
    user: dlib.ABCUser | None = None
    user_db: Type[dlib.ABCUser] = dlib.ABCUser.get_class()

    try:
        user = user_db.objectify_with_username(username=username)
    except dlib.ABCUserError as err:
        pass

    if user:
        db_token: Type[dlib.ABCToken] = dlib.ABCToken.get_class()
        token: str
        token, _ = db_token.create(token_type = dlib.ABCTokenType.EMAIL,
                                   username=user.get_username(),
                                   ip=request.client.host,
                                   agent=user_agent if user_agent else "None")

        print("> Send the code '{token}' to '{email}'.".format(email=user.get_email(), token=token))  # Fixme: Remove this line after debugging!!!

        system_settings = SystemSettings.get_system_settings()
        EMailHandler.send_email_in_background(background_tasks=background_task,
                                              subject="Token Verification",  # ToDo: Move to configuration
                                              email_to=[user.get_email()],
                                              include_setting_cc=False,
                                              body={"app_name": system_settings.app_name,
                                                    "full_name": user.get_firstname() + " " + user.get_lastname(),
                                                    "url": "http:/localhost:5000/api/auth/verify_email/" + token},  # Fixme: System URL from Config
                                              template_name = system_settings.mail_template_email_confirmation)


@router.get("/verify_email/{token}", tags = ["Lgout"])
def rest_get_verify_email(token: str):
    db_token: Type[dlib.ABCToken] = dlib.ABCToken.get_class()
    email_token: dlib.ABCToken

    try:
        email_token = db_token.objectify_token(token = token, token_type = dlib.ABCTokenType.EMAIL)
        email_token.test_token(token_type=dlib.ABCTokenType.EMAIL)
    except dlib.ABCTokenError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to verify token provided for user login.")  # Question: Message to config?
                            # headers={"WWW-Authenticate": "Bearer"})  # Question, what was that for?

    db_token.remove_token(email_token)

    user_db: Type[dlib.ABCUser] = dlib.ABCUser.get_class()
    user: dlib.ABCUser

    try:
        user = user_db.objectify_with_username(username=email_token.get_username())
    except dlib.ABCUserError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist.")  # Question: Message to config?

    user.accept_email(forceWrite=True)
