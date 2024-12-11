from pydantic import BaseModel, model_serializer
from typing import Optional, List, Union

class UnitTypeInputModel(BaseModel):
    value : Union[List[str],str]
    unit_tag : str 

class InputModel(BaseModel):
    value : float|str 
    unit_tag : str 
    
        
    @model_serializer()
    def serialize_model(self):
        
        return {self.unit_tag : self.value}

class UnitModel(BaseModel):
    tag : str 
    text : str 
    description : Optional[str] = None 
    priority : int 
    
    
class UnitTypeResponseModel(BaseModel):
    tag : str 
    text : str 
    priority : int
    has_feature_value : bool
    units : List[UnitModel]
    

class UnitInputResponseModel(BaseModel):
    unittype_tag : str 
    has_feature_value : bool = False
    unit_tag : str 
    unit_text : str 
    value : Union[str,float,int] 
    
    

    

    
        


