from pydantic import BaseModel
from typing import Optional

POLICY_TAG = "mitocube_policy"


class PolicyModel(BaseModel):
    tag : str = POLICY_TAG
    title : Optional[str] = None
    text : str = ""
    required : bool = False
    version : int = 0
    created_at : Optional[float] = None
    updated_at : Optional[float] = None
    updated_by : Optional[str] = None


class PolicyUpdateModel(BaseModel):
    title : Optional[str] = None
    text : str
    required : bool = False
    bump_version : bool = False     # True → all users must agree again


class PolicyStatusModel(BaseModel):
    required : bool       # is agreement currently required
    agreed : bool         # has this user agreed
    must_agree : bool     # required and not agreed → user is blocked
    version : int