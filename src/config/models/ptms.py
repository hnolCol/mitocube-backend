from pydantic import BaseModel
from typing import Optional, List


class PTMSiteBaseModel(BaseModel):
    """
    A post translational modification site. The tag is the protein tag followed by the
    position and the modification, e.g. P12345_S473_PHOSPHO.
    A PTM site is supported by one or multiple modified precursors (the evidence) and is
    quantified per sample via a [:QUANTIFIED] relationship.
    """
    tag : str
    protein_group_tag : str
    protein_tag : Optional[str] = None
    position : int
    modification : str
    residue : Optional[str] = None
    precursor_tags : List[str] = []


class PTMSiteInsertModel(PTMSiteBaseModel):
    """
    Model for inserting a PTM site. The site is linked to the given protein group via
    [:OF_PROTEIN_GROUP] and to the supporting precursors via [:SUPPORTED_BY].
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
