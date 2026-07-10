from pydantic import BaseModel
from typing import Optional, Dict, List 

class PhenotypeModel(BaseModel):
    tag : str 
    text: str 
    created_at: Optional[float] = None 
    description: Optional[str] = None
    group_tag: str #phenotype group 
    group_text: str #phenotype group text to classfiy the phenotypes 
     
     
class PhenotypeInputModel(BaseModel):
    tag: Optional[str] = None
    text: str
    description: Optional[str] = None
    group_tag: Optional[str] = None
    group_text: Optional[str] = None
    
class PhenotypeGenotypeInput(BaseModel):
    phenotype_tag : str 
    attributes : Dict[str,List[str]] # attribute.tag : [trait.tag]
    genotype_tag: str 
    created_at: Optional[float] = None 

     
     
     
     