from enum import Enum

class PATScopeEnum(str, Enum):
    """Scopes that can be granted to a personal access token (PAT).

    A PAT only grants access to endpoints that explicitly require one of
    its scopes; it never acts as a general login session.
    """
    QC_UPLOAD = "qc.upload"
