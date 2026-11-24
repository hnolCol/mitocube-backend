from pydantic import BaseModel, Field, field_validator, field_serializer
from typing import List, Optional
import time 
class InstrumentStateModel(BaseModel):
    
    tag : str 
    text : str 
    description : str 
    color : str 

class InstrumentInfoModel(BaseModel):
    """Free text info (e.g. technician contact, service contract) attached to an instrument.
    Stored on a dedicated InstrumentInfo node, one per instrument, via (:Trait)-[:HAS_INFO]->(:InstrumentInfo)."""
    instrument_tag : str
    text : str = ""
    created_at : Optional[float] = None
    created_by : Optional[str] = None
    modified_at : Optional[float] = None
    modified_by : Optional[str] = None

class InstrumentInfoUpdateModel(BaseModel):
    "Payload for updating the info text of an instrument."
    text : str = Field(..., max_length=10000)




class InstrumentsStateResponseModel(BaseModel):
    tag : str 
    created_at : float 
    comment : Optional[str] = None 
    
class InstrumentStateHistoryModel(BaseModel):
    "Model for a instrument state history"
    tag : Optional[str] = None #the tag of the history item
    instrument_tag : str 
    state_tag : str 
    started_at : float 
    duration : Optional[float] = None #if it is the latest state there is no duration. -> calculate in gui to "now"
    ended_at : Optional[float] = None
    
    @field_validator("duration")
    def validate_duration(cls, v : float, info):
        if v is None:
            return (time.time() * 1000) - info.data["started_at"]
        return v

class InstrumentStateHistoryResponseModel(InstrumentStateHistoryModel):
    ""

class SampleMeasuringInsertModel(BaseModel):
    """Payload for marking a sample as currently being measured (live data).

    Marks the sample identified by the sample_tag as being measured, optionally
    on the given instruments. A PAT with the 'sample.measuring' scope (or curator
    rights) is required. Setting it again refreshes the measurement timestamp and
    instruments."""
    sample_tag : str
    instrument_tags : List[str] = []


class SampleMeasuringResponseModel(BaseModel):
    """A live measurement of a sample, connected to the sample and, if given,
    to the instrument Trait nodes it is being measured on. Stored on a dedicated
    LiveMeasurement node, one per sample, via (:Sample)-[:BEING_MEASURED]->(:LiveMeasurement)."""
    tag : str
    sample_tag : str
    instrument_tags : List[str] = []
    created_at : float
    updated_at : float
    created_by : Optional[str] = None
