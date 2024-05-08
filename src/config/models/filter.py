from pydantic import BaseModel
from typing import Optional, List 

class FilterProps(BaseModel):
    tag : str 
    proteome_id : str 
    description : str 
    publication : Optional[str] = None
    protein_tags : List[str]



class Filter(BaseModel):
    tag : str 
    proteome_id : str 
    description : str 
    created_at : float
    modified_at : float = None 
    
    

