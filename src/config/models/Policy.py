from pydantic import BaseModel, model_validator
from typing import Optional
from services.encryption import create_hierarchical_hash

TERMS_OF_USE = "terms_of_use"
DATA_PROTECTION = "data_protection"

# order = order in which users are asked to agree
POLICY_TYPES = [TERMS_OF_USE, DATA_PROTECTION]


class PolicyModel(BaseModel):
    tag : str
    type : str                      # terms_of_use | data_protection
    title : Optional[str] = None
    text : str = ""
    required : bool = False
    version : int = 1
    created_at : Optional[float] = None
    created_by : Optional[str] = None
    updated_at : Optional[float] = None
    updated_by : Optional[str] = None


class PolicyInsertModel(BaseModel):
    type : str
    title : str
    text : str
    required : bool = False
    tag : str = ""

    @model_validator(mode="after")
    def generate_tag(self):
        if self.type not in POLICY_TYPES:
            raise ValueError(f"type has to be one of {POLICY_TYPES}")
        self.tag = create_hierarchical_hash([self.type, self.title])[:20]
        return self


class PolicyUpdateModel(BaseModel):
    title : Optional[str] = None
    text : str
    required : bool = False
    bump_version : bool = False     # True -> archive the current version, all users must agree again


class PolicyVersionModel(BaseModel):
    policy_tag : str
    version : int
    title : Optional[str] = None
    text : str = ""
    required : bool = False
    updated_at : Optional[float] = None     # when this version was written
    updated_by : Optional[str] = None
    archived_at : Optional[float] = None    # when it was replaced by a newer version


class PolicyStatusModel(BaseModel):
    tag : str
    type : str
    title : Optional[str] = None
    required : bool       # is agreement currently required
    agreed : bool         # has this user agreed to the current version
    must_agree : bool     # required and not agreed -> user is blocked
    version : int
