from pydantic import BaseModel
from typing import Optional

class DiseaseModel(BaseModel):
    tag: str                       
    text: str                       # disease name
    description: Optional[str] = None
    created_at: Optional[float] = None

class DiseaseInputModel(BaseModel):
    tag: str
    text: str
    description: Optional[str] = None