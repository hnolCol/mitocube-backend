from typing import List, Dict, Optional
from time import time
from pydantic import BaseModel, Field 

from config.enums.states import SubmissionStatesEnums, SubmissionStateColors
from services.enums import get_enum_as_dict, get_inversed_enum_as_dict, get_enum_values_as_list_of_strings


class StateResponse(BaseModel):
    """State response"""
    states : Dict[str,int] = get_enum_as_dict(SubmissionStatesEnums)
    states_inv : Dict[int,str] = get_inversed_enum_as_dict(SubmissionStatesEnums)
    colors : Dict[str,str] = get_enum_as_dict(SubmissionStateColors)
    colors_inv : Dict[int,str] = get_enum_as_dict(SubmissionStateColors,SubmissionStatesEnums)



class StateChangeModel(BaseModel):
    """State Change Model"""
    craeted_on : float = Field(..., default_factory=time) 
    prev_state : SubmissionStatesEnums
    state : SubmissionStatesEnums
    comment : Optional[str] = None