from pydantic import BaseModel
from typing import List, Optional
from config.models.attributes import AttributeTree

class SampleModel(BaseModel):
    created_at : float 
    tag : str 
    text : str = None 
    index : int = None 
    
    
class SampleResponseModel(SampleModel):
    pass 


class SampleUpdateModel(BaseModel):
    genotype_tag: Optional[str] = None
    condition_applications: Optional[List[AttributeTree]] = None