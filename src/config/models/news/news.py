from pydantic import BaseModel 
from pydantic import EmailStr, Field
from typing import Optional, List 

from services.random_generators import get_random_string


class NewsInsertModel(BaseModel):
    tag : str = Field(...,default_factory=lambda : get_random_string(N = 6))
    content : str 
    title : Optional[str] = None 
    submission_tags : Optional[List[str]] = []
    feature_tags : Optional[List[str]] = []
    user_tag : Optional[str] = None
    
class NewsModel(BaseModel):
    tag : str
    content : str
    title : Optional[str] = None 
    created_at : Optional[float] = None
    modified_at : Optional[float] = None 
    submission_tags : Optional[List[str]] = []
    feature_tags : Optional[List[str]] = []
    user_tag : str 
    
    


    
    
