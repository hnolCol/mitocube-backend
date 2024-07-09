from pydantic import BaseModel, field_validator
from typing import Optional, List 

class FilterProps(BaseModel):
    tag : str
    text : str 
    proteome_id : str 
    description : str 
    publication : Optional[str] = None
    protein_tags : List[str]

    @field_validator("tag", mode="after")
    def check_tag(cls, v : str) -> str:
        ""
        print(v)
        if v is None:
            print(cls.text)
            return cls.text.replace(" ","_").lower() 
        return v 
        
class Filter(BaseModel):
    tag : str 
    proteome_id : str 
    description : str 
    created_at : float
    modified_at : float = None 
    publication : Optional[str] = None 
    
    

