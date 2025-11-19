from pydantic import BaseModel, field_validator
from typing import Optional, List

class SymptomModel(BaseModel):
    
    tag : str 
    text : str 
    description : str 
    priority : int 
    s : Optional[str] = None
    
    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    


class SymptomInsertModel(SymptomModel):
    pass

class SymptomResponseModel(BaseModel):
    tag : str 
    text : str 
    description : str 
    priority : int 