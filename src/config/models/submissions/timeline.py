from typing import Optional, List
from time import time 
from pydantic import BaseModel, Field
from config.models.submissions.states import SubmissionStatesEnums
from services.random_generators import get_random_string

class TimeLineEntryModel(BaseModel):
    """
    Timeline Entry Model of a submission/dataset that 
    describes an alteration such as a state change. 
    """
    id : int 
    label : str = Field(...,default_factory=get_random_string)
    created_on : float = Field(..., default_factory=time)
    user_tag : str  = None
    user_label : str = None
    state : SubmissionStatesEnums
    comment : Optional[str] = None 

class TimeLineModel(BaseModel):
    """
    Timeline Model that holds the information of the
    process of the submission. 
    """
    created_on : float = Field(..., default_factory=time) 
    modified_on :float = Field(..., default_factory=time) 
    label : str = Field(...,default_factory=get_random_string)
    entries : List[TimeLineEntryModel] = []


