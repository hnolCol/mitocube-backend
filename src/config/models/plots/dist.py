from pydantic import BaseModel


class DistResponseModel(BaseModel):
    min : float
    q1 : float
    median : float
    q3 : float
    max : float
    mean : float
    std : float
    count : int
    
    
     