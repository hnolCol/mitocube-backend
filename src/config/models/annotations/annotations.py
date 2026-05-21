from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from services.random_generators import get_random_string
from datetime import datetime




class AnnotationGroupsInsertModel(BaseModel):
    """
    Model for inserting annotation groups. 
    """
    # tag: str = Field(..., min_length=5, max_length=5, default_factory=lambda: get_random_string(5))
    text: str
    description: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None

class AnnotationGroupsModel(AnnotationGroupsInsertModel):
    """
    Groups annotations into categories
    (e.g. mitochondrial proteome annotations).
    """
    tag : str
    created_at: Optional[float] = None # timestamp
    created_by: Optional[str] = None # user tag

    class Config:
        from_attributes = True



class AnnotationsModel(BaseModel):
    """
    Model for annotation datasets. 
    (e.g. MitoCarta 3.0, MitoCOP).
    """
    
    tag: str = Field(..., min_length=5, max_length=5, default_factory=lambda: get_random_string(5))
    text: str
    description: str
    publication: Optional[str] = None
    pubmed_id: Optional[str] = None
    source:  Optional[str] = None
    protein_tags: Optional[List[str]] = []
    group_tag: str

    @field_validator("protein_tags", mode="before")
    @classmethod
    def validate_protein_tags(cls, v : str):
        if isinstance(v, str):
            if ";" in v:
                str.str
                return [vi.strip() for vi in v.split(";")]
            if "\n" in v:
                return [vi.strip() for vi in v.split("\n")]
            return [v]
        if isinstance(v, list):
            return [vi.strip() for vi in v]
        raise ValueError("protein_tags must be a string or a list of strings.")

    class Config:
        from_attributes = True


    