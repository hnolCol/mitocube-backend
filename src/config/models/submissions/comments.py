from pydantic import BaseModel, Field 
from typing import List 
from services.date import get_time_stamp
from services.random_generators import get_random_string

    
class SubmissionCommentModel(BaseModel):
    tag : str = Field(..., default_factory=lambda : get_random_string(N = 5))
    created_at : float = Field(..., default_factory=get_time_stamp)
    user_tag : str | None = None
    content : str 
    tags : List[str] = []
    response_to: str | None = None
    
    