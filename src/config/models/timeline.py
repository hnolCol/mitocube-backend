from typing import List 
from pydantic import BaseModel, Field 

from services.date import get_time_stamp
from services.random_generators import get_random_string
from config.enums.states import SubmissionStatesEnums


class TimelineInputModel(BaseModel):
    created_at : float = Field(default_factory=get_time_stamp)
    tag : str = Field(...,min_length=8,max_length=8,default_factory=lambda : get_random_string(8))
    content : str 
    submission_state : SubmissionStatesEnums 
    submission_tag : str 
    user_tag : str 
    
    

class TimelineModel(BaseModel):
    created_at : float = Field(default_factory=get_time_stamp)
    tag : str 
    content : str 
    submission_state : SubmissionStatesEnums 
    submission_tag : str 
    user_tag : str #the user who craeted the timeline 
    
    class Config:
        use_enum_values = True 
    

class SubmissionTimelineResponseModel(BaseModel):
    submission_state : SubmissionStatesEnums #
    submission_tag : str 
    timeline : List[TimelineModel] #order by the time. line/(ordering could als be implemented in the model)



