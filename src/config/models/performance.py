from pydantic import BaseModel, field_validator
from typing import Dict, Optional, List
from enum import Enum


class QCPeptideModel(BaseModel):
    sequence : str 
    description : Optional[str] = None 
    protein_tag : str 
    


class QCPeptidesModel(BaseModel):
    user_tag : str 
    peptides : List[QCPeptideModel]

    


class QCStandardType(str, Enum):
    """
    Types of QC standards, e.g. a digested cell lysate or a single protein such as BSA.
    """

    CELL_LYSATE = "Cell lysate"
    PROTEIN = "Protein"


class QCStandardModel(BaseModel):
    """
    Describes the sample (standard) that was used to generate a QC run, e.g. a HeLa digest or BSA.
    Standards are immutable after creation, hence there is no update.
    """

    tag : str
    vendor : str
    type : QCStandardType


class QCPrecursorModel(BaseModel):
    """
    A specific precursor that was quantified in a QC run. Only a subset of precursors is recorded
    for QC purposes since the full quantification data has no biological meaning and is too large.
    """

    precursor_tag : str
    value : Optional[float] = None
    score : Optional[float] = None
    retention_time : Optional[float] = None


class QCPrecursorsModel(BaseModel):
    """
    Collection of specific precursors that were quantified in a QC run.
    """

    run_tag : str
    precursors : List[QCPrecursorModel]


class QCRunModel(BaseModel):
    """
    A quality control run. A run is always linked to the instrument it was acquired on and
    to the QC standard (e.g. HeLa digest, BSA) that was used to generate it.
    """
    tag : str 
    instrument_name_tag : str 
    user_tag : str 
    qc_standard_tag : str
    rt_peptides : Dict[str,float]
    quant_proteins : int 
    quant_peptides : int 
    quant_precursors : int
    quant_protein_groups : int
    qc_precursors : List[QCPrecursorModel] = []
    group_attr : Dict[str, List[str]] #the attributes and attribute values that creates a group /e.g. the 
    #performance runs are analysed and visualized together. A group attribute should be anything that 
    #has an significant effect on the performance. 
    
