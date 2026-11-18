import os
from functools import lru_cache

from fastapi import HTTPException, status

from config.models.user import UserModel
from config.settings.general import get_general_settings
from services.json import read_json


@lru_cache()
def terms_of_use_exist() -> bool:
    """Returns True if a terms-of-use document is actually in place.

    The check fails closed only when a real document exists: the configured
    file must be present and contain actual terms. A missing file, an empty
    or placeholder document (empty JSON object, no content keys) means no
    terms are in force and the agreement check is skipped entirely.
    """
    settings = get_general_settings()
    path = settings.use_terms_file
    if path is None or not os.path.exists(path):
        return False
    try:
        document = read_json(path)
    except Exception:
        return False
    if not isinstance(document, dict) or len(document) == 0:
        return False
    content_keys = ("data_policy_sections", "summary_points", "sections", "text", "title")
    return any(document.get(key) for key in content_keys)


def raise_if_terms_not_accepted(user : UserModel, db = None) -> None:
    """Raises 403 if a required policy is in force and the user has not agreed to it.

    The policies (terms of use, data protection) live in the policy collection of
    the database and the frontend asks for agreement via the policy endpoints.
    Deployments without a required policy do not enforce anything, so logins
    without any defined terms of use pass.
    """
    if db is None or not user:
        return
    statuses = db.policy.get_status(user_tag = user.tag)
    if any(status.must_agree for status in statuses):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="The terms of use have not been accepted yet. "
                                   "Please read and accept the terms of use to access the API.")


def is_terms_exempt_path(path : str) -> bool:
    """Returns True for the endpoints that must stay reachable without accepted
    terms: fetching the terms document, accepting it, and the login-state probe."""
    if path == "/api/info/terms":
        return True
    if path == "/api/auth/token/valid":
        return True
    if path.startswith("/api/auth/user/") and path.endswith("/useterms"):
        return True
    if path == "/api/policy" or path.startswith("/api/policy/"):
        return True
    return False
