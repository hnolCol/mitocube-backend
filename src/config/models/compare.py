from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Literal, ForwardRef



CompareModel = ForwardRef('CompareModel')

class CompareModel(BaseModel):
    submission_tag : str 
    type : Literal["and","or","not","trend","pairwise","annotation"]
    criteria : Literal["significant", "significant_decrease", "significant_increase", "not_significant", "increasing", "decreasing", "has_annotation","does_not_have_annotation"] = "significant"
    id : str
    children : Optional[List[CompareModel]] = []
    props : Optional[dict] = {}