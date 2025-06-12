from pydantic import BaseModel, model_validator, Field 
from services.random_generators import get_random_string

from typing import Optional, List

class MaintenanceBaseModel(BaseModel):
    "A Maintenance model describing the procedure for the maintenance"
    tag : str 
    text : str 
    description : str 
    
    
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
    maintenance_tags : List[str] 
    instrument_tag : str 
    user_tag : str
    description : Optional[str] = None 
    costs : Optional[float] = 0 

class MaintenanceEventInsertModel(MaintenanceEventBaseModel):
    
    tag : str = Field(...,min_length=12, max_length=12, default_factory=lambda : get_random_string(12))
    
    
class MaintenanceEventModel(MaintenanceEventBaseModel):
    "Model describing the maintenance that was performed on an instrument on a given date (timestamp)"
    timestamp : float 