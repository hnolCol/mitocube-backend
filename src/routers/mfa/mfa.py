import pyotp
import qrcode
import io
import base64

from fastapi import APIRouter, Depends, BackgroundTasks,  HTTPException
from routers.authentication.token import create_access_token, get_time_stamp
from config.models.user import UserModel
from config.models.mfa import MFASetupResponse, MFAEnableRequest, MFAStatusResponse, MFADisableRequest
from config.settings.general import get_general_settings
from config.settings.token import get_user_token_settings, get_mfa_settings
from services.users import get_user_from_token, check_mfa_setup_token, check_pending_mfa_token
from services.encryption import verify_password
from config.exceptions.HTTPExceptions import (
    mfa_already_enabled, mfa_not_setup, mfa_code_invalid, mfa_not_enabled, user_blocked, user_not_found
)
from cryptography.fernet import Fernet

from lib.database.Database import Database
from config.models.token.token import TokenResponse
DB = Database.DB()
GENERAL_SETTINGS = get_general_settings()
TOKEN_SETTINGS = get_user_token_settings()
MFA_SETTINGS = get_mfa_settings()
fernet = Fernet(MFA_SETTINGS.MFA_ENCRYPTION_KEY.get_secret_value())

router = APIRouter(
    prefix="/api/auth/mfa",
    tags=["Token", "Authentication", "MFA"]
)


@router.get("/status", response_model=MFAStatusResponse,
            response_description="Returns whether MFA is currently enabled for the user.")
def get_mfa_status(user: UserModel = Depends(get_user_from_token)):
    return MFAStatusResponse(mfa_enabled=user.mfa_enabled)

@router.post("/setup", response_model=MFASetupResponse)
def setup_mfa(token: dict = Depends(check_mfa_setup_token)):
    user_tag = token["tag"]
    if not DB.users.exists(tag=user_tag):
        raise user_not_found
    user = DB.users.get_user_by_tag(user_tag)
    if user is None:
        raise user_blocked

    secret = pyotp.random_base32()
    encrypted_secret = fernet.encrypt(secret.encode()).decode()
    if not DB.users.update(tag=user_tag, user_props={"mfa_secret": encrypted_secret}):
        raise HTTPException(status_code=500, detail="Could not store MFA secret.")

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name=GENERAL_SETTINGS.app_name)

    return MFASetupResponse(secret=secret, qr_code=uri, token=create_access_token({"tag": user_tag, "purpose": "mfa_setup"}, expires_delta=TOKEN_SETTINGS.expires_after_minutes))


@router.post("/enable", response_model=TokenResponse)
def enable_mfa(payload: MFAEnableRequest, token: dict = Depends(check_mfa_setup_token)):
    user_tag = token["tag"]
    db_user = DB.users.get_user_by_tag(user_tag)
    if db_user is None or not db_user.mfa_secret:
        raise mfa_not_setup
    # Decrypt the MFA secret
    db_user.mfa_secret = fernet.decrypt(db_user.mfa_secret.encode()).decode()

    totp = pyotp.TOTP(db_user.mfa_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise mfa_code_invalid

    if not DB.users.update(tag=user_tag, user_props={"mfa_enabled": True}):
        raise HTTPException(status_code=500, detail="Could not enable MFA.")

    # Enrollment complete — mint the real, fully verified session now.
    user = DB.users.get_user_by_tag(user_tag)
    jwt_token = create_access_token(
        user.model_dump(), key_subset=["tag"],
        add_dict={"verified": True, "verified_at": get_time_stamp()},
    )
    return TokenResponse(success=True, token=jwt_token, verified=True,
                          role=user.role, firstname=user.firstname,
                          lastname=user.lastname, tag=user.tag,
                          mfa_enabled=True)


@router.post("/disable", response_description="Disables MFA. Requires password and a valid current MFA code.")
def disable_mfa(payload: MFADisableRequest, user: UserModel = Depends(get_user_from_token)):
    """
    Requires both password and a valid TOTP code — disabling MFA is
    security-sensitive, so a single factor (just the session token)
    shouldn't be enough to turn it off.
    """
    print(payload)
    if not user.mfa_enabled:
        raise mfa_not_enabled

    db_user = DB.users.get_user_by_tag(user.tag)
    if db_user is None or db_user.password is None:
        raise HTTPException(status_code=404, detail="User not found.")

    if not verify_password(payload.password, db_user.password.get_secret_value()):
        raise HTTPException(status_code=401, detail="Password is incorrect.")

    totp = pyotp.TOTP(db_user.mfa_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise mfa_code_invalid

    if not DB.users.update(tag=user.tag, user_props={"mfa_enabled": False, "mfa_secret": None}):
        raise HTTPException(status_code=500, detail="Could not disable MFA.")

    return {"success": True, "message": "MFA disabled successfully."}