from pydantic_settings import BaseSettings 
from pydantic import BaseModel 
from typing import List, Dict

class MetaText(BaseModel):
    """"""
    id : int = None
    tag : str  #data_anaylsis , linked_data, 
    title : str
    text : str


class MetaTexts(BaseSettings):
    """
    Base settings to defined metatexts for a proeject
    submission
    """
    titles : List[str] = ["Research Aim","Experimental Procedure","Additional information"]
    placeholders = Dict[str:str] = {
        "Research Aim" : "Please enter some background information about your project. Think about it like a small abstract in a paper.",
        "Experimental Procedure" : "Please provide detailed information about the experimental procedure.",
        "Additional information" : "Here you can add additional information such as batch effects."
        }
    required : Dict[str:bool] = {
        "Research Aim" : True,
        "Experimental Procedure" : True,
        "Additional information" : False
        }
    min_text_length : Dict[str:int] = {
        "Research Aim" : 100,
        "Experimental Procedure" : 50,
        "Additional information" : 0
        }
    tags : {
        "Research Aim" : "metatext:research_aim",
        "Experimental Procedure" : "metatext:experimental_procedure",
        "Additional information" : "metatext:add_info"
    }
    


