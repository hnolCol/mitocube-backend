from pydantic import BaseModel, field_validator
from typing import Dict, Optional, List 


class PerformanceRunModel(BaseModel):
    ""
    tag : str 
    instrument_tag : str 
    user_tag : str 
    rt_peptides : Dict[str,float]
    quant_proteins : int 
    quant_peptides : int 
    group_attr : Dict[str:List[str]] #the attributes and attribute values that creates a group /e.g. the 
    #performance runs are analysed and visualized together. A group attribute should be anything that 
    #has an significant effect on the performance. 
    
    @field_validator("group_attr")
    def check_group_attributes(cls, v : Dict[str,List[str]]):
        "Checks the group attributes"
        #TO DO import settings and check for mandatory attributes such as att_ms_instrument, att_ms_type 
        return v 
        
    
class PerformanceRunResponse(BaseModel):
    ""
    


