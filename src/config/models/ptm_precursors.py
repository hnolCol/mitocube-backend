from pydantic import BaseModel, model_validator
from typing import Optional, List

from config.models.precursors import PrecursorInsertModel


class PTMModificationModel(BaseModel):
    """
    A single modification of a PTM precursor. position is the 1-based position of the
    modified residue in the protein sequence. modification is a UniMod accession (e.g. "21"),
    name (e.g. "Phospho") or monoisotopic mass (e.g. "79.966331") and is resolved to a UniMod
    entry at insert time; unimod_id and unimod_name are filled with the resolved values.
    """
    position: int
    modification: str
    residue: Optional[str] = None
    unimod_id: Optional[int] = None
    unimod_name: Optional[str] = None


class PTMPrecursorInsertModel(PrecursorInsertModel):
    """
    Model for inserting a PTM precursor (a modified precursor, e.g. a phosphopeptide).
    The precursor tag is derived from the (modified) sequence and the charge state
    (sequence.charge), exactly like an unmodified precursor. The precursor is connected
    to the given protein groups and maps to one PTMSite per entry in modifications via
    [:MAPS_TO], so single- and multi-modified peptides (e.g. double phospho) are supported.
    Quantification is done at the precursor level via Sample-[:QUANTIFIED]->Precursor.
    """
    protein_tag: str
    modifications: List[PTMModificationModel]

    @model_validator(mode="after")
    def validate_modifications(self):
        if len(self.modifications) == 0:
            raise ValueError("A PTM precursor requires at least one modification.")
        positions = [m.position for m in self.modifications]
        if len(set(positions)) != len(positions):
            raise ValueError(f"Duplicate modification positions in {positions}.")
        return self

    def ptm_site_tags(self) -> List[str]:
        """Derives the PTMSite tags this precursor maps to, e.g. P12345_S473_PHOSPHO."""
        return [f"{self.protein_tag}_{m.position}_{(m.unimod_name or m.modification).upper()}" for m in self.modifications]
