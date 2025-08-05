from pydantic import BaseModel, field_validator, field_serializer, HttpUrl
from typing import Optional, List

class SparepartModel(BaseModel):
    tag : str 
    text : str 
    company : str 
    description : str 
    product_id : str
    price : Optional[int|float] = 0  
    s : Optional[str] = None
    link : Optional[HttpUrl] = ""
    
    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    
    @field_serializer("link")
    def serialize_url(self, url: HttpUrl, _info):
        return str(url)
    
    
class SparepartResponseModel(BaseModel):
    tag : str 
    text : str 
    description : str 
    company : str 
    product_id : str 
    price: Optional[int|float] = 0 
    link : Optional[HttpUrl] = ""
    