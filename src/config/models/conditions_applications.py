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
    

# ca = ConditionApplicationTreeModel()
# def transform_for_ui(item : ConditionApplicationTreeModel, r : List = None) -> List[Dict]:
#     if r is None:
#         r = []
    
#     r.append({
#         "type" : "attribute",
#         "tag" : item.attribute_tag,
#         "children" : [
#             {
#                 "type" : "trait",
#                 "tag" : item.trait_tag,
#                 "value" : item.value,
#                 "children" : [transform_for_ui(r = [], item = child) for child in item.children]
#             }
#         ]
#     })
#     return r




class ConditionApplicationTreeResponseModel(ConditionApplicationTreeModel):
    ""
    

class ConditionApplicationAttributeModel(BaseModel):
    attribute_tag : str 
    condition_application_tags : List[str] 
