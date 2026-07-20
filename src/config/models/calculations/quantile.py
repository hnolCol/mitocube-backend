from pydantic import BaseModel 
from typing import Optional


class QuantileModel(BaseModel):
    tag : Optional[str] = None
    min : float 
    q25: float 
    m: float 
    q75: float 
    max: float 
    N: int
    outlier_removed: Optional[bool] = False
    
