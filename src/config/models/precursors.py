from pydantic import BaseModel
from typing import Optional, List


class PrecursorBaseModel(BaseModel):
    """Base model for precursors. The tag is the sequence followed by the charge state, e.g. PEPTIDEK.2"""
    tag: str
    sequence: str
    charge: int


class PrecursorResponseModel(PrecursorBaseModel):
    """Model for precursors."""
    mz: Optional[float] = None
    im: Optional[float] = None
    protein_group_tag: Optional[str] = None
    protein_group_tags: Optional[List[str]] = None
    quantified: bool = False


class PrecursorInsertModel(PrecursorBaseModel):
    """Model for inserting precursors. The precursor is connected to one or multiple protein groups.
    mz is the mass-to-charge ratio of the precursor and im the optional ion mobility value
    (e.g. from timsTOF instruments, not all data contains ion mobility). value is the
    log2 intensity of the precursor quantification. score is the identification score of the precursor
    (e.g. DIA-NN or Spectronaut score).
    The retention time is not stored on the precursor node since it is setup specific
    (column, gradient) and therefore has no ground truth. It is only stored on the
    [:QUANTIFIED] relationship per acquisition.
    """
    mz: Optional[float] = None
    im: Optional[float] = None
    value: Optional[float] = None  # log2 intensity of the precursor quantification
    score: Optional[float] = None
    protein_group_tags: List[str]
