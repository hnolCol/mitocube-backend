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


class QCStandardBaseModel(BaseModel):
    """
    Describes the sample (standard) that was used to generate a QC run, e.g. a HeLa digest or BSA.
    Standards are immutable after creation, hence there is no update and no edit model.
    """

    tag : str
    vendor : str
    type : QCStandardType


class QCStandardInsertModel(QCStandardBaseModel):
    """
    Model for inserting a QC standard.
    """
    pass


class QCStandardResponseModel(QCStandardBaseModel):
    """
    Model for returning a QC standard.
    """
    pass


class QCPrecursorBaseModel(BaseModel):
    """
    A specific precursor that was quantified in a QC run. Only a subset of precursors is recorded
    for QC purposes since the full quantification data has no biological meaning and is too large.
    """

    precursor_tag : str
    value : Optional[float] = None
    score : Optional[float] = None
    retention_time : Optional[float] = None


class QCPrecursorInsertModel(QCPrecursorBaseModel):
    """
    Model for inserting a QCPrecursor.
    """
    pass


class QCPrecursorResponseModel(QCPrecursorBaseModel):
    """
    Model for returning a QCPrecursor.
    """
    pass


class QCPrecursorsModel(BaseModel):
    """
    Collection of specific precursors that were quantified in a QC run.
    """

    run_tag : str
    precursors : List[QCPrecursorInsertModel]


class QCRunBaseModel(BaseModel):
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
    group_attr : Dict[str, List[str]] #the attributes and attribute values that creates a group /e.g. the 
    #performance runs are analysed and visualized together. A group attribute should be anything that 
    #has an significant effect on the performance. 
    


class QCRunInsertModel(QCRunBaseModel):
    """
    Model for inserting a QC run. The specific precursors (QCPrecursorInsertModel) can be
    provided directly with the run or added separately via the run's precursors endpoint.
    """
    qc_precursors : List[QCPrecursorInsertModel] = []


class QCRunResponseModel(QCRunBaseModel):
    """
    Model for returning a QC run.
    """
    created_at : Optional[int] = None
    qc_precursors : List[QCPrecursorResponseModel] = []
    
