from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status, Request
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

import lib.data as dlib
from lib.data.mem import MemLoginTokens, MemUserTokens, ABCLoginTokenError
import lib.data.sql.postgresql as psql

from lib.rest.security import rest_verify_user_token, RestSessionInformation
from lib.rest.pmodels.auth.tokens import UserTokenPRM  # Pydantic Response Models
from lib.rest.pmodels.auth.tokens import TokenVerificationCodePPM  # Pydantic Post Models

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Question: rename or alternative path for login? How to differentiate between user_token and api_token?
# Question: rename to user_token (or login_token)?  /share to api_token or rest_token?
@router.post("/token", response_description="Returns a jwt token after login .", response_model=UserTokenPRM)
def rest_post_request_email_login_token(background_task: BackgroundTasks,
                                   request: Request,
                                   user_agent: Annotated[str | None, Header()] = None,
                                   form_data: OAuth2PasswordRequestForm = Depends()) -> UserTokenPRM:  # Question, was UserModel, does it has to be a pedantic model?

    # ToDo: Create Function within rest.security.verify_login
    # Question, should always a token be requested? theoretically one could gues password until login token request screen pops up
    # GUI Solution, best way, send username only to request token, and send token plus username password on second page, disadvantage, someone could bother one with emails... requires a timeout for emails
    # BACKEND Solution:, save password with the login token and validate it after second step ... someone could bother one with emails... requires a timeout for emails

    # system_settings = SystemSettings.get_system_settings()
    # ToDo: Option to disallow logins? makes no sense currently due to restart of system required anyway to update config...
    user: dlib.ABCUser

    try:
        user = psql.PostgreSQLUser.objectify_with_email(email=form_data.username)  # Fixme: fix the method/function? Login with both?
    except dlib.ABCUserError as err:  # ToDo: Implement ABCUserNotExistError(ABCUserError) and similar everywhere
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})

    try:
        user.login(password=form_data.password)  # user._test_password(password=form_data.password):
        # ToDo: Above, user last login date is already set, but login not validated...
    except dlib.ABCUserError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})

    db_login_tokens = MemLoginTokens()
    verification_code: str = db_login_tokens.create_token(username=user.get_username(),
                                                          ip=request.client.host,
                                                          agent=user_agent if user_agent else "None")

    db_session_tokens = MemUserTokens()
    token_session: str = db_session_tokens.create_token(username=user.get_username(),
                                                        ip=request.client.host,
                                                        agent=user_agent if user_agent else "None")
    db_session_tokens._write()  # Fixme: remove me

    print("> Send the code '{code}' to '{email}'.".format(email=user.get_email(),
                                                          code=verification_code, ))  # Fixme: Remove this line after debugging!!!

    # EMailHandler.send_email_in_background(background_tasks=background_task,  # Fixme: Enable me!
    #                                       subject="Token Verification",  # ToDo: Move to configuration
    #                                       email_to=[user.get_email()],
    #                                       include_setting_cc=False,
    #                                       body={"app_name": system_settings.app_name,
    #                                             "first_name": user.get_lastname(),
    #                                             "verification_code": verification_code},
    #                                       template_name=system_settings.mail_template_verification)

    return UserTokenPRM(success=True,
                        token=token_session,  # Question Is that actually used?
                        verified=False,
                        role=-1,  # former UserRolesEnum GUEST = 0 - STANDARD = 1 - CURATOR = 2 - ADMIN = 4  # Question: good to display role, but to verfiy own function and raise Exception?
                        label=None,  # Question, remove and replace with id (below)
                        id=None,
                        firstname=None,
                        lastname=None,
                        msg=None)


@router.post("/token/verify",
             response_description="Returns a jwt that is verified by a one-time password and is valid for 48 hours.",
             response_model=UserTokenPRM)
def rest_post_verify_email_login_token(token_to_verify: TokenVerificationCodePPM,
                                  request: Request,
                                  user_agent: Annotated[str | None, Header()] = None) -> UserTokenPRM:

    # ToDo: Create Function within rest.security.verify_login_token

    user: dlib.ABCUser

    db_login_tokens = MemLoginTokens()
    db_session_tokens = MemUserTokens()

    try:
        verification_code = db_login_tokens.test_token(token = token_to_verify.verification_code,
                                                       ip = request.client.host,
                                                       agent = user_agent if user_agent else "None")
    except ABCLoginTokenError as err:
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user login.",
                            headers={"WWW-Authenticate": "Bearer"})

    if verification_code.is_expired():
        # Question: Log message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user login.",
                            headers={"WWW-Authenticate": "Bearer"})
    elif verification_code.get_ip() != request.client.host:
        # Question: Log message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user login.",
                            headers={"WWW-Authenticate": "Bearer"})
    elif verification_code.get_agent() != user_agent if user_agent else "None":
        # Question: Log message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unable to verify token provided for user login.",
                            headers={"WWW-Authenticate": "Bearer"})

    try:
        user = psql.PostgreSQLUser.objectify_with_username(username=verification_code.get_username())
    except dlib.ABCUserError as err:  # ToDo: Implement ABCUserNotExistError(ABCUserError) and similar everywhere
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Unable to verify token provided for user login.",
                            headers={"WWW-Authenticate": "Bearer"})

    # Question, generating a new one? what happens with the last one?
    token_session: str = db_session_tokens.create_token(username=verification_code.get_username(),
                                                        ip=request.client.host,
                                                        agent=user_agent if user_agent else "None")
    db_session_tokens._write()  # Fixme: remove me

    return UserTokenPRM(success=True,
                        token=token_session,  # Question Is that actually used?
                        verified=True,
                        role=4,  # UserRolesEnum.ADMIN,  # Fixme: get from user class!  # Question: Is that used? afterwards GUI requests /api/users/roles
                        label=user.get_username(),  # Todo, remove and replace with id (below)
                        id=user.get_id(),
                        firstname=user.get_firstname(),
                        lastname=user.get_lastname(),
                        msg=None)


@router.get("/token/valid",
            response_description="Checks if a token from local storage is valid and returns the user's role and details",
            response_model=UserTokenPRM)
def rest_get_verify_user_token(session: RestSessionInformation = Depends(rest_verify_user_token)) -> UserTokenPRM:
    user = session.get_user()

    return UserTokenPRM(success=True,
                        token=session.get_token().get_token(),  # Question Is that actually used?
                        verified=True,
                        role=4,  # UserRolesEnum.ADMIN,  # Fixme: get from user class!  # Question: Is that used? afterwards GUI requests /api/users/roles
                        label=user.get_username(),  # Todo, remove and replace with id (below)
                        id=user.get_id(),
                        firstname=user.get_firstname(),
                        lastname=user.get_lastname(),
                        msg=None)



# ToDo: /token/share
# @router.post("/token/share",
#              summary="Share tokens can be used to push qc runs to the app without login in every time. Creating a share token requires admin rights and the application specific password.")
# def create_share_token(inputPassword: ShareTokenPassword, user : UserModel = Depends(is_user_admin)):


