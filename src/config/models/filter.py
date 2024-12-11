from pydantic import BaseModel, field_validator
from typing import Optional, List 

class FilterProps(BaseModel):
    tag : str
    text : str 
    proteome_tag : str 
    description : str 
    publication : Optional[str] = None
    protein_tags : List[str]

    @field_validator("tag", mode="after")
    def check_tag(cls, tag : str) -> str:
        "If the tag is none, set it"
        if tag is None:
            return cls.text.replace(" ","_").lower() 
        return tag 
        
class FilterModel(BaseModel):
    tag : str 
    text : str 
    proteome_tag : str 
    description : str 
    created_at : float
    modified_at : float = None 
    publication : Optional[str] = None 
    N : int 
    
    

