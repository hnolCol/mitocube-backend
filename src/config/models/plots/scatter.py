from pydantic import BaseModel
from typing import List, Tuple, Dict

class ScatterDataResponse(BaseModel):
    """"""
    dataset_label : str 
    key_names  : List[Dict[str,str]] #the keynames to exctract the data





