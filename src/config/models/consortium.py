from pydantic import BaseModel, EmailStr, field_validator
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

    @field_validator("url", mode="before")
    @classmethod
    def check_url(cls, v):
        if v is None or (isinstance(v, str) and len(v) == 0):
            return None
        from urllib.parse import urlparse
        if not isinstance(v, str) or not urlparse(v).scheme in ("http", "https") or not urlparse(v).netloc:
            raise ValueError("url must be a valid http(s) website address, e.g. https://consortium.org")
        return v


class ConsortiumGroupInput(BaseModel):
    group_tags : List[str]
