from fastapi.security import  OAuth2PasswordRequestForm
from fastapi import Depends, Request
from pydantic import EmailStr
from typing import List, Tuple

from services.encryption import verify_password, get_decoded_token
from config.exceptions.HTTPExceptions import (
    user_form_data_incorrect,
    credentials_exception,
    user_blocked,
    user_role_too_low,
    token_not_valid_exception,
    submission_tag_not_found,
)
from config.models.user import UserModel, UserRolesEnum, PublicUser
from lib.database.abstract.Database import DatabaseABC
from lib.database.Database import get_db

from lib.cache.user_cache import get_cached_user, cache_user


def check_mfa_setup_token(token: dict = Depends(get_decoded_token)) -> dict:
    if token.get("purpose") != "mfa_setup":
        raise token_not_valid_exception
    if "tag" not in token:
        raise token_not_valid_exception
    return token


def check_pending_mfa_token(token: dict = Depends(get_decoded_token)) -> dict:
    """Ensures the token is a pending-MFA token (issued by /token, not yet verified).
    Rejects fully verified tokens, share tokens, or anything else — this token
    type should only ever be usable against /verify.
    """
    if token.get("purpose") != "mfa_pending":
        raise token_not_valid_exception
    if "tag" not in token:
        raise token_not_valid_exception
    return token


def are_public_users_allowed(user_tags : List[str], db : DatabaseABC = Depends(get_db)) -> List[bool]:
    """Checks if a list of Users are allowed to login."""
    users_from_db = db.users.get_users_by_tags(tags = user_tags)
    return [u.allow_login for u in users_from_db if u is not None]


def get_client_ip(request : Request) -> str:
    """Returns the real client IP, honoring X-Forwarded-For from trusted proxies.

    Production runs behind nginx, so request.client.host is the proxy IP
    for every request. The forwarded header is only trusted when the
    direct peer is a configured proxy; otherwise a spoofed header would
    let attackers rotate fake IPs and evade the rate limit.
    """
    from config.settings.token import get_mfa_settings

    direct = request.client.host if request.client else "unknown"
    trusted = [ip.strip() for ip in get_mfa_settings().TRUSTED_PROXY_IPS.split(",") if ip.strip()]
    if direct in trusted:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # first entry = originating client
            return forwarded.split(",")[0].strip()
    return direct


def get_user_from_login(form_data : OAuth2PasswordRequestForm = Depends(), db : DatabaseABC = Depends(get_db), request : Request = None) -> UserModel:
    """Returns the user from a login.

    Rate limited per email and per client IP: too many failed attempts
    within the configured window raise 429 instead of hitting the
    password check, blocking brute-force attempts on both a single
    account and a single origin.
    """
    from lib.mfa.mfa import mfa_runtime
    from config.exceptions.HTTPExceptions import login_rate_limited

    email_key = f"email:{form_data.username}"
    if mfa_runtime.is_login_rate_limited(email_key):
        raise login_rate_limited
    if request is not None:
        ip_key = f"ip:{get_client_ip(request)}"
        if mfa_runtime.is_login_rate_limited(ip_key):
            raise login_rate_limited

    user  = db.users.get_user_by_email(form_data.username)
    #user verification check
    user_in_db = check_user_allowed(user is not None, user)
    if not verify_password(form_data.password, user_in_db.password.get_secret_value()):
        mfa_runtime.register_login_failure(email_key)
        if request is not None:
            mfa_runtime.register_login_failure(ip_key)
        raise credentials_exception

    mfa_runtime.reset_login_failures(email_key)
    if request is not None:
        mfa_runtime.reset_login_failures(ip_key)
    return user_in_db


def check_user_allowed(user_exists : bool, user : UserModel) -> UserModel:
    """Checks if user is allowed to login

    Parameters
    ----------
    user_exists : bool 
        If the user exists. 
    user : UserModel
        The user to check

    Returns
    -------
    UserModel
        The user if checks are passed, otherwise raises an HTTP Exception. 

    Raises
    ------
        HTTP Exception
            if user form data is incorrect
        HTTP Exception
            if user param allow_login is False 
    """
    if not user_exists:
        raise user_form_data_incorrect
    if not user.allow_login:
        raise user_blocked
    return user


def check_token_verified(token : str =  Depends(get_decoded_token)) -> str:
    """Check if the token is verified. Raises an exception if not."""
    if "verified" in token and token["verified"]:
        return token 
    raise token_not_valid_exception


def get_user_from_token(token = Depends(check_token_verified), db : DatabaseABC = Depends(get_db)) -> UserModel:
    """Extracts the user from a token. The user is looked up in the Mongo
    user cache first (short TTL) and only fetched from Neo4j on a cache miss.
    Secrets (password, mfa_secret) are never cached."""
    if "tag" not in token : raise token_not_valid_exception
    user = get_cached_user(token["tag"])
    if user is not None:
        return check_user_allowed(user is not None, user)
    user_in_db = db.users.get_user_by_tag(tag = token["tag"])

    user  = check_user_allowed(user_in_db is not None,user_in_db)
    if user is not None:
        cache_user(user)
    return user 


def is_user_at_least_curator(user : UserModel = Depends(get_user_from_token)) -> UserModel:
    """Checks if the user is at least curator.
    raises an exception if the userrole is not at least curator."""
    if (user.role >= UserRolesEnum.CURATOR):
        return user
    raise user_role_too_low


def is_user_admin(user : UserModel = Depends(get_user_from_token)) -> UserModel:
    """Checks if the user is at least admin.
    raises an exception if the userrole is not admin."""
    if (user.role >= UserRolesEnum.ADMIN):
        return user
    raise user_role_too_low


def is_creator_of_submission_or_curator(submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> UserModel:
    """Checks if the user is the creator of the submission.
    raises an exception if the user is not the creator of the submission."""
    if not db.submissions.exists(tag = submission_tag):
        raise submission_tag_not_found
    creator_tag = db.submissions.get_creator(tag = submission_tag)
    if user.tag == creator_tag:
        return user 
    else:
        if user.role >= UserRolesEnum.CURATOR:
            return user
    raise user_role_too_low
