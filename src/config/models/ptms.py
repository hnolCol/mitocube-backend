from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List


class PTMSiteBaseModel(BaseModel):
    """
    A post translational modification site. The tag is derived from the protein tag,
    the position and the modification, e.g. P12345_S473_PHOSPHO. If no protein tag is
    given (group level identification where the position is ambiguous across the
    proteins of the group), the tag is derived from the protein group tag instead,
    e.g. pg12345_S473_PHOSPHO.
    A PTM site is supported by one or multiple modified precursors (the evidence) and is
    quantified per sample via a [:QUANTIFIED] relationship.
    """
    tag : Optional[str] = None
    protein_group_tag : str
    protein_tag : Optional[str] = None
    position : int
    modification : str
    residue : Optional[str] = None
    sequence_window : Optional[str] = None #the sequence window around the modification, e.g. the flanking residues; although derivable from the protein sequence it is stored since it is what the search engine localized against
    precursor_tags : List[str] = []

    @model_validator(mode="after")
    def derive_tag(self):
        """
        Derives the tag from the protein tag (or the protein group tag if no protein tag
        is given), the position and the modification. If a tag is provided it must match
        the derived tag, otherwise a ValueError is raised to prevent tags that lie about
        what they identify.
        """
        base_tag = self.protein_tag if self.protein_tag is not None else self.protein_group_tag
        derived_tag = f"{base_tag}_{self.position}_{self.modification}"
        if self.tag is not None and self.tag != derived_tag:
            raise ValueError(f"The tag {self.tag} does not match the derived tag {derived_tag} (protein/group tag, position, modification).")
        self.tag = derived_tag
        return self


class PTMSiteInsertModel(PTMSiteBaseModel):
    """
    Model for inserting a PTM site. The tag is derived and validated from the protein
    tag (or protein group tag), the position and the modification. The site is linked
    to the given protein group via [:OF_PROTEIN_GROUP] and to the supporting precursors
    via [:SUPPORTED_BY].
    value is the log2 intensity of the site quantification, score the identification
    score and site_localization the localization probability (e.g. from DIA-NN or
    Spectronaut) of the modification within the site.
    """
    value : Optional[float] = None
    score : Optional[float] = None
    site_localization : Optional[float] = None


class PTMSiteResponseModel(PTMSiteBaseModel):
    """
    Model for returning a PTM site.
    """
    quantified : bool = False
