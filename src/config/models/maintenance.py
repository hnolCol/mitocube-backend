from pydantic import BaseModel, model_validator, Field 
from services.random_generators import get_random_string

from typing import Optional, List

class MaintenanceBaseModel(BaseModel):
    "A Maintenance model describing the procedure for the maintenance"
    tag : str 
    text : str 
    description : Optional[str] = None 
    
    
    
# class MaintenanceInsertModel(MaintenanceBaseModel):
#     "The insert model for a maintenance event. This is used to insert a new maintenance event into the database."
#     tag : str = Field(..., min_length=12, max_length=12, default_factory=lambda : get_random_string(12)) #create random tag 
#     instrument_state_tag : str 
#     instrument_tag : str
    
class MaintenanceInsertModel(MaintenanceBaseModel):

    s : Optional[str] = None 
    priority : int
    
    @model_validator(mode = "after")
    def set_s(self) -> None:
        
        if self.s is None:
            self.s =  " ".join([s.lower() for s in [self.tag, self.text,self.description]])
    
class MaintenanceResponseModel(MaintenanceBaseModel):
    "The response model of a maintenance."
    
    
class MaintenanceEventBaseModel(BaseModel):
    "Model describing the maintenance that was performed on an instrument on a given date (timestamp)"
    tag : str
    instrument_state_tag : str
    maintenance_procedure_tags : Optional[List[str]] = []
    symptom_tags :Optional[List[str]] = []
    instrument_tag : str 
    user_tag : Optional[str] = None
    description : Optional[str] = None 
    costs : Optional[float] = 0.0
    sparepart_tags : Optional[List[str]] = []



class MaintenanceEventInsertModel(MaintenanceEventBaseModel):
    state_tag : str = "state.maintenance.open"
    tag : str = Field(...,min_length=12, max_length=12, default_factory=lambda : get_random_string(12))
    
class MaintenanceEventModel(MaintenanceEventBaseModel):
    "Model describing the maintenance that was performed on an instrument on a given date (timestamp)"
    created_at : float 
    
class MaintenanceProcedureResponseModel(MaintenanceBaseModel):
    "The response model for a maintenance procedure"
    priority : int = 500
    
class MaintenanceStateResponseModel(BaseModel):
    "The response model for a maintenance state"
    tag : str 
    text : str 
    color : str
    description : Optional[str] = None 
