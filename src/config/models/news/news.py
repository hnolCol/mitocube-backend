from pydantic import BaseModel 
from pydantic import EmailStr, Field
from typing import Optional, List 

from services.random_generators import get_random_string

class NewsModel(BaseModel):
    tag : str = Field(...,default_factory=lambda : get_random_string(N = 5))
    content : str
    title : Optional[str] = None 
    created_at : Optional[float] = None
    modified_at : Optional[float] = None 
    submission_tags : Optional[List[str]] = []
    feature_tags : Optional[List[str]] = []
    user_tag : str 
    
    


    
    
