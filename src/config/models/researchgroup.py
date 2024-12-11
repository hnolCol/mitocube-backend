from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from services.random_generators import get_random_string 

class ResearchGroupModel(BaseModel):
    created_at : Optional[float] = None 
    tag : str 
    name : str 
    abbreviation : str 
    email : EmailStr
    address: str 
    
class ResearchGroupResponseModel(ResearchGroupModel):
    n_users : Optional[int] = None 
    n_datasets : Optional[int] = None
    
class ResearchGroupInput(ResearchGroupModel):
    tag : str = Field(...,min_length=8,max_length=8,default_factory=lambda : get_random_string(8))
    
    