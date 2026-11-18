from fastapi import HTTPException, status

from config.models.user import UserModel


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
    terms: fetching the policies and accepting them, and the login-state probe."""
    if path == "/api/auth/token/valid":
        return True
    if path == "/api/policy" or path.startswith("/api/policy/"):
        return True
    return False
