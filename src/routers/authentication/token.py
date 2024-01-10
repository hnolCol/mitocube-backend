import time 

from fastapi import APIRouter, BackgroundTasks, Depends, Body

from config.models.user import UserModel
from config.models.token.token import TokenVerificationCode, TokenResponse, ShareTokenPassword, TokenValidResponse
from config.settings.general import get_general_settings
from config.settings.email import get_email_settings

from services.date import get_time_stamp
from services.mail import send_email_in_background
from services.random_generators import get_random_string
from services.users import get_user_from_login, check_user_allowed, is_user_admin, get_user_from_token
from services.encryption import create_access_token, check_for_verification_code_in_token, check_share_token_password
from config.exceptions.HTTPExceptions import verification_code_incorrect, share_token_pw_incorrect

from lib.user.UserHandling import UserDB

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()
router = APIRouter(
    prefix="/api/auth/token",
    tags=["Token", "Authentication"]
    )


# @router.get("/user")
# def get_users(user : UserModel = Depends(is_user_admin)):
#     """
#     Returns a list of users.
#     """
#     print(user)
#     users = UserDB.get_users()
#     return users

@router.post("/", response_description="Returns a jwt token after login .", response_model=TokenResponse)
def login_for_access_token(background_task : BackgroundTasks, 
                           user : UserModel = Depends(get_user_from_login), 
                           verification_code : str = Depends(lambda : get_random_string(12))) -> TokenResponse:
    """
    Returns a jwt token upon successful login that contains a verification code as well the user label.
    The verification code is send to the mail stored in the database and the token can be validated
    with the verification code. 

    Parameters
    ----------
    background_task : BackgroundTasks
        FastAPI background task to send email. 
    user : UserModel
        The user that is extracted from the token, by default Depends(get_user_from_login)
    verification_code : str
        The verification code , by default Depends(lambda : get_random_string(12))

    Returns
    -------
    TokenResponse
        The response of the HTTP Request. 
    """
    #create jwt token with just the id and the verification code
    jwt_token = create_access_token(user.model_dump(),
                                    key_subset=["label"],
                                    add_dict={
                                        "verification_code" : verification_code,
                                        })

    send_email_in_background(
        background_tasks=background_task,
        subject="Token Verification",
        email_to=[user.email],
        cc = [],
        body={
            "app_name" : GENERAL_SETTINGS.app_name,
            "first_name" : user.firstname,
            "verification_code" : verification_code
        },
        template_mame=EMAIL_SETTINGS.mail_verification_template
    )

    return TokenResponse(success=True,token=jwt_token,verified=False)



@router.get("/valid", response_description="Checks if a token from local storage is valid and returns the user's role and details",
            response_model=TokenValidResponse)
def check_token(user : UserModel = Depends(get_user_from_token)):
    """
    Checks if a token from local storage is valid and returns the user's role and details. 
    
    Parameters
    ----------
    user : UserModel
    
    Returns
    -------
    TokenValidResponse 
        If the token is valid a response is made, otherwise a HTTP Exception is raise in the Depends(get_user_from_token)
    """
    return TokenValidResponse(
        success=True,
        role = user.role, 
        verified = True, 
        firstname=user.firstname, 
        lastname=user.lastname, 
        label=user.label)

@router.post("/verify", 
             response_description="Returns a jwt that is verified by a one-time password and is valid for 48 hours.", 
             response_model=TokenResponse)
def verify_token_by_code(verification : TokenVerificationCode, 
                         decoded_token: dict = Depends(check_for_verification_code_in_token)):
    """
    Verifies jwt by comparing the verification code that has been sent by mail to the one hidden in the jwt token.
    
    """
    if verification.verification_code != decoded_token["verification_code"]:
        raise verification_code_incorrect
    #get user by id 
    user_label = decoded_token["label"]
    user_exists, user_in_db = UserDB.get_user_by_label(user_label)
    user : UserModel = check_user_allowed(user_exists, user_in_db)

    jwt_token = create_access_token(user.model_dump(),
                                    key_subset=["label"],
                                    add_dict={"verified" : True, 
                                              "verified_at" : get_time_stamp()})
    
    return TokenResponse(success=True, token = jwt_token, verified=True, role=user.role, firstname = user.firstname, lastname=user.lastname, label=user.label)

### Share Token

@router.post("/share", 
             summary="Share tokens can be used to push qc runs to the app without login in every time. Creating a share token requires admin rights and the application specific password.")
def create_share_token(inputPassword: ShareTokenPassword, user : UserModel = Depends(is_user_admin)):
    """
    Share tokens require user admin rights as well as a password which is defined in the env file.
    """
    if check_share_token_password(inputPassword.pw):
        jwt_token = create_access_token(user.model_dump(), key_subset=["id"], add_dict={"created_at" : get_time_stamp()}, share_token=True)
        return TokenResponse(success=True,token= jwt_token,verified=False, role=0)
    raise share_token_pw_incorrect




