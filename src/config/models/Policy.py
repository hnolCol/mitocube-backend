from pydantic import BaseModel, model_validator
from typing import Optional
from services.encryption import create_hierarchical_hash


class PolicyModel(BaseModel):
    tag : str
    title : Optional[str] = None
    text : str = ""
    required : bool = False
    version : int = 0
    created_at : Optional[float] = None
    updated_at : Optional[float] = None
    updated_by : Optional[str] = None


class PolicyInsertModel(BaseModel):
    title : str
    text : str
    required : bool = False
    tag : str = ""

    @model_validator(mode="after")
    def generate_tag(self):
        self.tag = create_hierarchical_hash([self.title])[:20]
        return self


class PolicyUpdateModel(BaseModel):
    title : Optional[str] = None
    text : str
    required : bool = False
    bump_version : bool = False     # True -> all users must agree again


class PolicyStatusModel(BaseModel):
    tag : str
    title : Optional[str] = None
    required : bool       # is agreement currently required
    agreed : bool         # has this user agreed to the current version
    must_agree : bool     # required and not agreed -> user is blocked
    version : int