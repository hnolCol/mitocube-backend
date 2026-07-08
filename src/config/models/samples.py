from pydantic import BaseModel
from typing import List, Optional
from config.models.attributes import AttributeTree

class SampleModel(BaseModel):
    created_at : float 
    tag : str 
    text : str = None 
    index : int = None 
    excluded : bool = False
    
    
class SampleResponseModel(SampleModel):
    pass 


class SampleUpdateModel(BaseModel):
    text: Optional[str] = None
    genotype_tag: Optional[str] = None
    condition_applications: Optional[List[AttributeTree]] = None
    replicate: Optional[int] = None