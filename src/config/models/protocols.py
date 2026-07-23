
from pydantic import BaseModel, EmailStr, Field
from typing import Optional



class ProtocolBaseModel(BaseModel):
    tag : str
    title : str
    text : str
    user_tag : str
    created_at : Optional[float] = None
    modified_at : Optional[float] = None
    modified_user_tags : Optional[list] = Field(default_factory=list)
    submission_tags : Optional[list] = Field(default_factory=list) 
    url : Optional[str] = None 
    doi : Optional[str] = None
    pubmed_id : Optional[str] = None    
    
    
class InsertProtocolModel(BaseModel):
    title : str
    text : str
    url : Optional[str] = None 
    doi : Optional[str] = None
    pubmed_id : Optional[str] = None    
    
    
class UpdateProtocolModel(BaseModel):
    title : str
    text : str 
    url : Optional[str] = None 
    doi : Optional[str] = None
    pubmed_id : Optional[str] = None    
    
    
    