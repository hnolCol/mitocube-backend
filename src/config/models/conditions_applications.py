from pydantic import BaseModel
from typing import List, Optional, Literal, ForwardRef



class ConditionApplicationItemModel(BaseModel):
    tag : str 
    attribute_tag : str 
    trait_tag : str 
    value : Optional[str|float|int] = None
    label : Literal["ConditionValue", "ConditionApplication"] = None 

ConditionApplicationTreeModel = ForwardRef('ConditionApplicationTreeModel')

class ConditionApplicationTreeModel(BaseModel):
    trait_tag : str 
    attribute_tag : str 
    value : Optional[str|float|int] = None
    children : List[ConditionApplicationTreeModel] = []
    


class ConditionApplicationTreeResponseModel(ConditionApplicationTreeModel):
    ""
    

class ConditionApplicationAttributeModel(BaseModel):
    attribute_tag : str 
    condition_application_tags : List[str] 
class ConditionApplicationStateModel(BaseModel):
    state_tag : str|int
    condition_application_tags : List[str] 


class ConditionApplicationStateAttributeModel(BaseModel):
    state_tag : str|int
    attribute_conditions : List[ConditionApplicationAttributeModel] 
    