from pydantic import BaseModel, field_validator, field_serializer, AnyUrl, Field
from typing import Optional, List

from services.random_generators import get_random_string

class SparepartBaseModel(BaseModel):
    tag : str 
    text : str 
    company : str 
    description : str 
    product_id : str
    price : Optional[int|float] = 0  
    link : Optional[AnyUrl] = None
    
    @field_serializer("link")
    def serialize_url(self, url: AnyUrl, _info):
        return str(url)
    
class SparepartModel(SparepartBaseModel):
    s : Optional[str] = None

    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    
class SparepartInsertModel(SparepartBaseModel):
    tag : str = Field(...,min_length=8, max_length=8, default_factory=lambda : get_random_string(8))
    
    
class SparepartResponseModel(SparepartBaseModel):
    ""
    