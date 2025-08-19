from pydantic import BaseModel, field_validator, field_serializer, computed_field
from typing import Optional
import time 
class InstrumentStateModel(BaseModel):
    
    tag : str 
    text : str 
    description : str 
    color : str 




class InstrumentsStateResponseModel(BaseModel):
    tag : str 
    created_at : float 
    comment : str 
    
class InstrumentStateHistoryModel(BaseModel):
    "Model for a instrument state history"
    tag : str #the tag of the history item
    instrument_tag : str 
    state_tag : str 
    started_at : float 
    duration : Optional[float] = None #if it is the latest state there is no duration. -> calculate in gui to "now"
    ended_at : Optional[float] = None
    
    @field_validator("duration")
    def validate_duration(cls, v : float, info):
        if v is None:
            return time.time() - info.data["started_at"]
        return v

class InstrumentStateHistoryResponseModel(InstrumentStateHistoryModel):
    ""