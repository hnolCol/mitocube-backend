from pydantic import BaseModel 



class QuantileModel(BaseModel):
    min : float 
    q25: float 
    m: float 
    q75: float 
    max: float 
    N: int