from pydantic import BaseModel
from typing import Optional

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
    duration : Optional[float] = None #if it is the latest state there is no duration. -> calculate in gui to "now"
    started_at : float 
    ended_at : Optional[float] = None
    
    
class InstrumentStateHistoryResponseModel(InstrumentStateHistoryModel):
    ""