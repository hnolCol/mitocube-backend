import time

from datetime import datetime 
from typing import List 

from pydantic import BaseModel 
from pydantic import Field

from config.models.attributes import Attribute, AttributeValue

from services.random_generators import get_random_string

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


