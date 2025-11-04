from pydantic import BaseModel
from typing import List, Dict



class ProteinGroupQuantificationModel(BaseModel):
    tag : str # Protein group tag 
    sample_tag : str # Sample tag 
    value : float  # Quantification value (intensity, such as LFQ, iBAQ, TMT, etc)

class ProteinQuantificationBulkInsertModel(BaseModel):
    quantifications: List[ProteinGroupQuantificationModel]

class PrecursorQuantificationModel(BaseModel):
    tag : str # Peptide tag
    protein_group_tag : str # Parent protein tag may also be a protein group tag
    sample_tag : str
    charge : int # Charge of the peptide
    value : float # Quantification value (intensity, such as LFQ, iBAQ, TMT, etc)
    score : float = 0.0  # Score of the peptide
    rt : float # Retention time of the peptide

    
    
    
    
