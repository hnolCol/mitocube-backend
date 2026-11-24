from datetime import timedelta
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException, Request, status

from config.enums.users.pats import PATScopeEnum
from config.enums.users.roles import UserRolesEnum
from config.exceptions.HTTPExceptions import credentials_exception
from config.models.pat import PATResponseModel
from config.models.user import UserModel
from lib.database.abstract.Database import DatabaseABC
from lib.database.abstract.PATs import PAT_TOKEN_PREFIX, hash_pat_token
from lib.database.Database import get_db
from lib.mfa.mfa import mfa_runtime
from services.date import get_current_datetime
from services.terms import raise_if_terms_not_accepted
from services.users import check_user_allowed, get_user_from_token, is_user_at_least_curator


def get_pat_expires_at_epochmillis(expires_in_days : int) -> int:
    """Returns the expiration of a PAT in epoch milliseconds."""
    expires_at = get_current_datetime() + timedelta(days=expires_in_days)
    return int(expires_at.timestamp() * 1000)


def authenticate_pat(token : str, db : DatabaseABC) -> Tuple[UserModel, PATResponseModel]:
    """Resolves a plain PAT to its owner and metadata.

    Failed lookups are rate limited per token hash so tokens cannot be probed
    without throttling. Returns 401 for unknown, revoked or expired tokens.
    """
    token_hash = hash_pat_token(token)
    rate_key = f"pat:{token_hash}"
    if mfa_runtime.is_login_rate_limited(rate_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many failed attempts. Please try again later.")
    record = db.pats.get_by_hash(token_hash)
    if record is None:
        mfa_runtime.register_login_failure(rate_key)
        raise credentials_exception
    mfa_runtime.reset_login_failures(rate_key)
    user = check_user_allowed(True, db.users.get_user_by_tag(tag=record["user_tag"]))
    if user.role < UserRolesEnum.CURATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Personal access tokens are restricted to curators and admins.")
    raise_if_terms_not_accepted(user, db)
    pat = PATResponseModel(**record["pat"])
    db.pats.touch(pat.tag)
    return user, pat


def require_pat_scope(scope : PATScopeEnum, user : UserModel, pat_scopes : List[PATScopeEnum]) -> None:
    """Raises if the PAT does not carry the required scope."""
    if scope not in pat_scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"The token does not have the required scope '{scope.value}'.")


def get_user_from_pat_or_token(request : Request, db : DatabaseABC = Depends(get_db)) -> Tuple[UserModel, Optional[List[PATScopeEnum]]]:
    """Authenticates either a PAT (mcp_...) or a verified login JWT.

    PATs never act as a general session: they resolve to their owner, and the
    endpoint decides which scopes a PAT must carry. The returned scopes are
    None for a JWT login (the caller applies the normal role checks) and the
    PAT's scopes for a PAT login.
    """
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() == "bearer" and token.startswith(PAT_TOKEN_PREFIX):
        user, pat = authenticate_pat(token, db)
        return user, pat.scopes
    user = is_user_at_least_curator(user=get_user_from_token(token=token, db=db))
    return user, None


def get_curator_or_qc_upload_pat(request : Request, db : DatabaseABC = Depends(get_db)) -> UserModel:
    """Guards the QC run upload endpoints.

    Accepts either a verified curator login or a PAT that carries the
    'qc.upload' scope and belongs to a curator.
    """
    return get_guard_for_pat_scope(PATScopeEnum.QC_UPLOAD)(request, db=db)


def get_guard_for_pat_scope(scope : PATScopeEnum):
    """Builds a route guard for an endpoint that accepts either a verified
    curator login or a PAT that carries the given scope and whose owner has
    at least curator rights.
    """
    def guard(request : Request, db : DatabaseABC = Depends(get_db)) -> UserModel:
        user, pat_scopes = get_user_from_pat_or_token(request, db=db)
        if pat_scopes is None:
            return user
        require_pat_scope(scope, user, pat_scopes)
        if user.role < UserRolesEnum.CURATOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="The token owner must have at least curator rights.")
        return user
    return guard


get_curator_or_submissions_read_pat = get_guard_for_pat_scope(PATScopeEnum.SUBMISSIONS_READ)
get_curator_or_sample_measuring_pat = get_guard_for_pat_scope(PATScopeEnum.SAMPLE_MEASURING)
