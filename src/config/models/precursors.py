from pydantic import BaseModel
from typing import Optional, List


class PrecursorBaseModel(BaseModel):
    """Base model for precursors. The tag is the sequence followed by the charge state, e.g. PEPTIDEK.2"""
    tag: str
    sequence: str
    charge: int


class PrecursorResponseModel(PrecursorBaseModel):
    """Model for precursors."""
    protein_group_tag: Optional[str] = None
    protein_group_tags: Optional[List[str]] = None
    quantified: bool = False


class PrecursorInsertModel(PrecursorBaseModel):
    """Model for inserting precursors. The precursor is connected to a single protein group."""
    protein_group_tag: str
