from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from services.random_generators import get_random_string



class AnnotationGroupModel(BaseModel):
    """
    Groups annotations into categories
    (e.g. mitochondrial proteome annotations).
    """

    tag : str = Field(..., min_length=5, max_length=5, default_factory=lambda : get_random_string(5))
    name: str 
    description: Optional[str] = None

    class Config:
        from_attributes = True



class AnnotationModel(BaseModel):
    """
    Model for annotation datasets. 
    (e.g. MitoCarta 3.0, MitoCOP).
    """

    tag : str = Field(..., min_length=5, max_length=5, default_factory=lambda : get_random_string(5))
    description: str 
    group_tag: str 
    publication: Optional[str] = None
    pubmed_id: Optional[str] = None

    class Config:
        from_attributes = True


