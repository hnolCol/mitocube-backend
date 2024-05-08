from pydantic import BaseModel, model_serializer
from typing import Literal


class InputModel(BaseModel):
    value : float|str 
    unit_tag : str 
    
        
    @model_serializer()
    def serialize_model(self):
        
        return {self.unit_tag : self.value}

class UnitModel(BaseModel):
    tag : str 
    text : str 
    unit : str #base Unit


class UserUnitInput(BaseModel):
    ""
    time_unit : Literal["s","min","h","w","a"] = "s"
    value : float 
    unit  : UnitModel
    
    

    
        


