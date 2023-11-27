from typing import Optional, List
from time import time 
from pydantic import BaseModel, Field
from config.models.submissions.states import SubmissionStates
from services.random_generators import get_random_string

class TimelineEntry(BaseModel):
    """
    """
    id : int 
    label : str = Field(...,default_factory=get_random_string)
    created_on : float = Field(..., default_factory=time)
    user_label : str 
    state : SubmissionStates
    comment : Optional[str] = None 



class Timeline(BaseModel):
    """
    """
    created_on : float = Field(..., default_factory=time) 
    modified_on :float = Field(..., default_factory=time) 
    label : str = Field(...,default_factory=get_random_string)
    entries : List[TimelineEntry] = []


