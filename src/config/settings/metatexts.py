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
    titles : List[str] = ["Research Aim","Experimental Procedure","Additional Information"]
    placeholders : Dict[str,str] = {
        "metatext:research_aim" : "Please enter some background information about your project. Think about it like a small abstract in a paper.",
        "metatext:experimental_procedure" : "Please provide detailed information about the experimental procedure.",
        "metatext:add_info" : "Here you can add additional information such as batch effects."
        }
    required : Dict[str,bool] = {
        "metatext:research_aim" : True,
        "metatext:experimental_procedure" : True,
        "metatext:add_info" : False
        }
    min_text_length : Dict[str,int] = {
        "metatext:research_aim" : 100,
        "metatext:experimental_procedure" : 50,
        "metatext:add_info" : 0
        }
    names : Dict[str,str] = {
        "metatext:research_aim" : "Research Aim",
        "metatext:experimental_procedure" : "Experimental Procedure",
        "metatext:add_info" : "Additional Information"
    }
    tags : Dict[str,str] = {
        "Research Aim" : "metatext:research_aim",
        "Experimental Procedure" : "metatext:experimental_procedure" ,
        "Additional Information" : "metatext:add_info"
    }
    


