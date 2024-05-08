from pydantic_settings import BaseSettings 
from pydantic import BaseModel 
from typing import List, Dict
from config.enums.states import SubmissionStatesEnums

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
    titles : List[str] = ["Research Aim",
                          "Experimental Procedure",
                          "Additional Information",
                          "Protein Digestion",
                          "Liquid Chromatography and Mass Spectrometry"]
    placeholders : Dict[str,str] = {
        "metatext:research_aim" : "Please enter some background information about your project. Think about it like a small abstract in a paper.",
        "metatext:experimental_procedure" : "Please provide detailed information about the experimental procedure/sample preparation.",
        "metatext:add_info" : "Here you can add additional information such as batch effects.",
        "metatext:protein_digestion" : "Please describe the protein digestion method.",
        "metatext:lcms" : "Please add information about the LC-MS/MS method."
        }
    required : Dict[str,bool] = {
        "metatext:research_aim" : True,
        "metatext:experimental_procedure" : True,
        "metatext:add_info" : False,
        "metatext:protein_digestion" : True,
        "metatext:lcms" : True
        }
    min_text_length : Dict[str,int] = {
        "metatext:research_aim" : 100,
        "metatext:experimental_procedure" : 50,
        "metatext:add_info" : 0,
        "metatext:protein_digestion" : 50,
        "metatext:lcms" : 50
        }
    names : Dict[str,str] = {
        "metatext:research_aim" : "Research Aim",
        "metatext:experimental_procedure" : "Experimental Procedure",
        "metatext:add_info" : "Additional Information",
        "metatext:protein_digestion"  : "Protein Digestion",
        "metatext:lcms" : "Liquid Chromatography and Mass Spectrometry"
    }
    tags : Dict[str,str] = {
        "Research Aim" : "metatext:research_aim",
        "Experimental Procedure" : "metatext:experimental_procedure",
        "Additional Information" : "metatext:add_info",
        "Protein Digestion" : "metatext:protein_digestion",
        "Liquid Chromatography and Mass Spectrometry" : "metatext:lcms"
    }
    allowed_for_state : Dict[str,int] = {
        "metatext:research_aim" : SubmissionStatesEnums.SUBMITTED,
        "metatext:experimental_procedure" : SubmissionStatesEnums.SUBMITTED,
        "metatext:add_info" : SubmissionStatesEnums.SUBMITTED,
        "metatext:protein_digestion" : SubmissionStatesEnums.PROCESSED,
        "metatext:lcms" : SubmissionStatesEnums.MEASURING,
    }



