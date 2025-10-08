from pydantic import BaseModel 
from typing import List, Dict, Optional

class MetaTextSubmissionResponse(BaseModel):
    """"""
    titles : List[str]
    placeholders : Dict[str,str]
    required : Dict[str,bool]
    min_text_length : Dict[str,int]
    names : Dict[str,str]
    tags : Dict[str,str]
    allowed_for_state : Dict[str,int]
    
    
    
class MetaTextInsertModel(BaseModel):
    title : str 
    text : str 
    
    
class MetaTextResponseModel(BaseModel):
    tag : str 
    title : str 
    text : str 
   # submission_tag : str 
    created_at : float 
    updated_at : Optional[float] = None 
    created_by : str #user_tag 
    updated_by : Optional[str] = None #user_tag
    
    
    
class ResearchAimInsertModel(BaseModel):
    research_aim : str  