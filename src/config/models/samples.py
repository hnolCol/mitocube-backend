from pydantic import BaseModel, Field
from typing import List, Optional
from config.models.attributes import AttributeTree
from services.date import get_time_stamp
from services.random_generators import get_random_string

class SampleModel(BaseModel):
    created_at : float 
    tag : str 
    text : str = None 
    index : int = None 
    excluded : bool = False
    lost : bool = False
    
    
class SampleResponseModel(SampleModel):
    pass 


class SampleUpdateModel(BaseModel):
    text: Optional[str] = None
    genotype_tag: Optional[str] = None
    condition_applications: Optional[List[AttributeTree]] = None
    replicate: Optional[int] = None


class SampleCommentModel(BaseModel):
    tag : str = Field(..., default_factory=lambda : get_random_string(N = 5))
    created_at : float = Field(..., default_factory=get_time_stamp)
    user_tag : str | None = None
    content : str 
    response_to: str | None = None