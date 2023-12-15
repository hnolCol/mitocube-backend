from pydantic import BaseModel
from typing import Dict, List

class FeatureModel(BaseModel):
    """Base Model for a Feature"""
    uniprot_id : str 
    gene_name : str 
    protein_name : str 
    organism : str
    length : int

class FeatureDataResponseModel(BaseModel):
    """
    Response model for feature data.
    """
    feature_id : str
    attributes_samples : Dict[str, Dict]
    dataset_labels : List[str]  # labels of datasets
    data : Dict[str, List[Dict]]  # data key - dataset_label
