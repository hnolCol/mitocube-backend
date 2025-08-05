from pydantic import BaseModel 
from typing import List, Optional




class PeptideBaseModel(BaseModel):    
    """Base model for peptides."""
    tag: str
    sequence: str


class PeptideResponseModel(PeptideBaseModel):
    """Model for peptides."""
    protein_tag: Optional[str] = None
    start: Optional[int] = None # start position of the peptide in the protein sequence
    end: Optional[int] = None # end position of the peptide in the protein sequence
    protein_tags: Optional[List[str]] = None  # list of protein tags associated with the peptide

class PeptideInsertModel(PeptideBaseModel):
    """Model for inserting peptides. The start and end positions are connected to the protein entry
    Therefore the protein tag is required and a single tag is used."""

    protein_tag: str  # protein tag associated with the peptide
    start: int  # start position of the peptide in the protein sequence
    end: int  # end position of the peptide in the protein sequence
    
    
    
