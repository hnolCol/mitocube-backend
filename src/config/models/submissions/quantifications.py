from pydantic import BaseModel
from typing import List, Dict, Optional

class ProteinGroupQuantificationModel(BaseModel):
    tag : str # Protein group tag 
    sample_tag : str # Sample tag 
    value : float  # Quantification value (intensity, such as LFQ, iBAQ, TMT, etc)

class ProteinQuantificationBulkInsertModel(BaseModel):
    quantifications: List[ProteinGroupQuantificationModel]

class PrecursorQuantificationModel(BaseModel):
    tag : str # Precursor tag (peptide sequence followed by the charge state, e.g. PEPTIDEK.2)
    sample_tag : str # Sample tag
    value : float # Quantification value (log2 intensity of the precursor)
    score : Optional[float] = 0.0  # Score of the precursor identification (e.g. DIA-NN or Spectronaut score)
    rt : Optional[float] = None # Retention time of the precursor
    im : Optional[float] = None # Ion mobility of the precursor (e.g. from timsTOF instruments, not all data contains ion mobility)
