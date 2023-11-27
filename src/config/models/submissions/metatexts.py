from pydantic import BaseModel 
from typing import List, Dict

class MetaTextSubmissionResponse(BaseModel):
    """"""
    titles : List[str]
    placeholders : Dict[str,str]
    required : Dict[str,bool]
    min_text_length : Dict[str,int]
    names : Dict[str,str]
    tags : Dict[str,str]