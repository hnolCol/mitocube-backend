from pydantic import BaseModel, EmailStr
from typing import Optional, List


class ConsortiumModel(BaseModel):
    created_at : Optional[float] = None
    tag : str
    text : str
    abbreviation : str
    email : EmailStr
    profile_text : Optional[str] = None
    url : Optional[str] = None


class ConsortiumResponseModel(ConsortiumModel):
    n_groups : Optional[int] = None
    n_submissions : Optional[int] = None


class ConsortiumInput(BaseModel):
    text : str
    abbreviation : str
    email : EmailStr
    profile_text : Optional[str] = None
    url : Optional[str] = None


class ConsortiumGroupInput(BaseModel):
    group_tags : List[str]
