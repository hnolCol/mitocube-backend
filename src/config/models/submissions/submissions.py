import time

from datetime import datetime 
from typing import List, Dict

from pydantic import BaseModel 
from pydantic import Field
from pydantic import field_validator

from config.models.user import PublicUser
from config.models.attributes import Attribute, AttributeValue
from config.settings.metatexts import MetaTexts 

from services.random_generators import get_random_string



class NewSubmission(BaseModel):
    """Add a submission"""
    created_on : float = Field(..., default_factory= time.time)
    sampleNames : List[str]
    collaborators : List[PublicUser]
    attributeTable : List[Dict[str,List[AttributeValue]]]
    metatext : Dict[str,str]
    label : str = Field(...,min_length=10, max_length=10)
    title : str 
    datasetAttributeValues : Dict[str,List[AttributeValue]]
    datasetAttributes : List[Attribute]
    samplesAttributes : List[Dict]

    @field_validator("metatext")
    def validate_meta_text(cls, v : Dict[str,str], config):
        """"""
        meta_settings = MetaTexts()
        #check first presents of required metatexts
        
        required_titels_tags = [tag for tag, required in meta_settings.required.items() if required]
        
        if not all(tag in v for tag in required_titels_tags):
            raise ValueError(f"Not all required metatexts found. {required_titels_tags}")
        ## check for minimal length 
        min_length_not_met = [tag for tag, min_length in meta_settings.min_text_length.items() if tag in v and len(v[tag]) < min_length]
        if len(min_length_not_met) > 0:
            raise ValueError(f"Minimal length not met for {min_length_not_met}")

        return v 




class SubmissionIDResponse(BaseModel):
    """BaseModel for an API ID Submission response"""
    id: str = Field(default_factory= lambda : get_random_string(N=10))
    created_on : datetime = Field(default_factory= datetime.now)


class SubmissionResponse(BaseModel):
    """BaseModel for an API Submission of a submission"""
    data_id : str 
    craeted_on : datetime = time.time()
    attributes : List[Attribute]
    attribute_values : List[AttributeValue]


