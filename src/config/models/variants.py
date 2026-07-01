from pydantic import BaseModel
from typing import Optional

class VariantModel(BaseModel):
    tag: str                        # ClinVar variat ID
    title: str                      # e.g. NME6:c.494G>A
    clinical_significance: Optional[str] = None
    consequence: Optional[str] = None
    rsid: Optional[str] = None
    gene_symbol: Optional[str] = None
    disease_tag: Optional[str] = None    
    protein_tag: Optional[str] = None    
    created_at: Optional[float] = None

class VariantInputModel(BaseModel):
    tag: str
    title: str
    clinical_significance: Optional[str] = None
    consequence: Optional[str] = None
    rsid: Optional[str] = None
    gene_symbol: Optional[str] = None
    disease_tag: Optional[str] = None
    protein_tag: Optional[str] = None