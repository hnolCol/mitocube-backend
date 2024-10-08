import random
import string
from datetime import datetime, timedelta

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status, Request
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

# from jose import jwt, JWTError, ExpiredSignatureError

from api.pmodels.auth.tokens import UserTokenPRM  # Pydantic Response Models
from api.pmodels.auth.tokens import TokenVerificationCodePPM

from config import SystemSettings

import lib.data as dlib
from lib.data.mem import MemLoginTokens, MemUserTokens, ABCLoginTokenError, ABCUserTokenError
import lib.data.sql.postgresql as psql

from lib.io.com import EMailHandler

router = APIRouter(prefix="/api/auth",
                   tags=["Token", "Authentication"])


# Question: rename or alternative path for login? How to differentiate between user_token and api_token?
# Question: rename to user_token (or login_token)?  /share to api_token or rest_token?
@router.post("/token", response_description="Returns a jwt token after login .", response_model=UserTokenPRM)
def request_email_login_token(background_task: BackgroundTasks,
                              request: Request,
                              user_agent: Annotated[str | None, Header()] = None,
                              form_data: OAuth2PasswordRequestForm = Depends()) -> UserTokenPRM:  # Question, was UserModel, does it has to be a pedantic model?

    system_settings = SystemSettings.get_system_settings()
    user: dlib.ABCUser | None = None

    try:
        user = psql.PostgreSQLUser.objectify_with_email(email=form_data.username)  # Fixme: fix the method/function? Login with both?
    except dlib.ABCUserError as err:  # ToDo: Implement ABCUserNotExistError(ABCUserError) and similar everywhere
        # Question: Log ABCLoginTokenError message?
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})

    if not user.is_login_allowed():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})
    elif not user.test_password(password=form_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})

    verification_code: str = MemLoginTokens.create_token(username=user.get_username(),
                                                         ip=request.client.host,
                                                         agent=user_agent if user_agent else "None")

    token_session: str = MemUserTokens.create_token(username=user.get_username(),
                                                    ip=request.client.host,
                                                    agent=user_agent if user_agent else "None")

    print("> Send the code '{code}' to '{email}'.".format(email=user.get_email(),
                                                          code=verification_code, ))  # Fixme: Remove this line after debugging!!!

    EMailHandler.send_email_in_background(background_tasks=background_task,
                                          subject="Token Verification",  # ToDo: Move to configuration
                                          email_to=[user.get_email()],
                                          include_setting_cc=False,
                                          body={"app_name": system_settings.app_name,
                                                "first_name": user.get_lastname(),
                                                "verification_code": verification_code},
                                          template_name=system_settings.mail_template_verification)

    # return UserTokenPRM(success=True, token=token_session, verified=False)  # Fixme: Why does this throw an missing exception?!
    # pydantic_core._pydantic_core.ValidationError: 1 validation error for UserTokenPRM
    # Field required [type=missing, input_value={'success': True, 'token'...ied': False, 'role': -1}, input_type=dict]
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
def verify_email_login_token(token_to_verify: TokenVerificationCodePPM,
                             request: Request,
                             user_agent: Annotated[str | None, Header()] = None) -> UserTokenPRM:

    user: dlib.ABCUser | None = None

    try:
        verification_code = MemLoginTokens.test_token(token = token_to_verify.verification_code,
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
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})

    if verification_code.get_username() != user.get_username():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  # ToDo: Collect to central spot / library
                            detail="Could not validate credentials. Invalid Token, User not found or password incorrect.",
                            headers={"WWW-Authenticate": "Bearer"})

    token_session: str = MemUserTokens.create_token(username=verification_code.get_username(),
                                                    ip=request.client.host,
                                                    agent=user_agent if user_agent else "None")

    return UserTokenPRM(success=True,
                        token=token_session,  # Question Is that actually used?
                        verified=True,
                        role=4,  # UserRolesEnum.ADMIN,  # Fixme: get from user class!  # Question: Is that used? afterwards GUI requests /api/users/roles
                        label=user.get_username(),  # Todo, remove and replace with id (below)
                        id=user.get_id(),
                        firstname=user.get_firstname(),
                        lastname=user.get_lastname(),
                        msg=None)

# ToDo: Next
# INFO:     127.0.0.1:49582 - "GET /api/users/roles HTTP/1.1" 404 Not Found
# INFO:     127.0.0.1:41626 - "GET /api/info/keyfigures HTTP/1.1" 404 Not Found

# ToDo: /token/share
# @router.post("/token/share",
#              summary="Share tokens can be used to push qc runs to the app without login in every time. Creating a share token requires admin rights and the application specific password.")
# def create_share_token(inputPassword: ShareTokenPassword, user : UserModel = Depends(is_user_admin)):


# ToDo: /token/valid
# @router.get("/token/valid",
#             response_description="Checks if a token from local storage is valid and returns the user's role and details",
#             response_model=TokenValidResponse)
# def check_token(user: UserModel = Depends(get_user_from_token)):
