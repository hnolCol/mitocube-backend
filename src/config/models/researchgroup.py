from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from services.random_generators import get_random_string 

class ResearchGroupModel(BaseModel):
    created_at : Optional[float] = None 
    tag : str 
    text : str 
    abbreviation : str 
    email : EmailStr
    address: str 
    institute : str
    url : Optional[str] = None
    
    
class ResearchGroupResponseModel(ResearchGroupModel):
    n_users : Optional[int] = None 
    n_datasets : Optional[int] = None
    
class ResearchGroupInput(BaseModel):
    text : str 
    abbreviation : str 
    email : EmailStr
    address: str 
    institute : str
    url : Optional[str] = None
    
    
class ResearchGroupResponseModel(ResearchGroupModel):
    pass 

    