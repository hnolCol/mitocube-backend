from pydantic import BaseModel, model_serializer
from typing import Literal, List


class InputModel(BaseModel):
    value : float|str 
    unit_tag : str 
    
        
    @model_serializer()
    def serialize_model(self):
        
        return {self.unit_tag : self.value}

class UnitModel(BaseModel):
    tag : str 
    text : str 
    priority : int 
    
    
class UnitTypeResponseModel(BaseModel):
    tag : str 
    text : str 
    priority : int
    units : List[UnitModel]
    


class UserUnitInput(BaseModel):
    ""
    time_unit : Literal["s","min","h","w","a"] = "s"
    value : float 
    unit  : UnitModel
    
    
    

    

    
        


