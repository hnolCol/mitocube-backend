from pydantic import BaseModel, field_validator
from typing import List, Optional

class APIParamString(BaseModel):
    param : Optional[List[str]] = None
    
    @field_validator('param', mode="before")
    def check_param(v : str|List[str] = None) -> List[str]:
        if v is None: return None
        if isinstance(v,str):
            if len(v) == 0: return None
            return v.split(";")
        if isinstance(v,list): return v 
        return v

class APIParamInt(BaseModel):
    param : Optional[List[int]] = None 
    
    @field_validator('param', mode="before")
    def check_param(v : int|List[int] = None) -> List[str]:
        if v is None: return None
        if isinstance(v,str):
            return [int(x) for x in v.split(";")]
        if isinstance(v,int): return [v]
        return v