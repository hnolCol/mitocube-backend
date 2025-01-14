from pydantic import BaseModel 
from typing import Optional


class QuantileModel(BaseModel):
    text : Optional[str] = None
    min : float 
    q25: float 
    m: float 
    q75: float 
    max: float 
    N: int
    
